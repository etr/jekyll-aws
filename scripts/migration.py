"""Render migration changes onto each stack's actual template; never redeploy a stale template."""

import argparse
import copy
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class CloudFormationLoader(yaml.SafeLoader):
    pass


def intrinsic(loader, tag, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    return {tag if tag in ("Ref", "Condition") else "Fn::" + tag: value}


CloudFormationLoader.add_multi_constructor("!", intrinsic)


def load_template(path):
    return yaml.load(Path(path).read_text(), Loader=CloudFormationLoader)


def edge_resources(name=None, redirects=None):
    code = (ROOT / "cloudfront/clean-urls.js").read_text()
    code = code.replace("var legacyRedirects = {};", "var legacyRedirects = " + json.dumps(redirects or {}) + ";")
    return {
        "CleanUrlsFunction": {
            "Type": "AWS::CloudFront::Function",
            "Properties": {
                "Name": name or {"Fn::Sub": "${ProjectName}-clean-urls"},
                "AutoPublish": True,
                "FunctionConfig": {"Comment": "Canonical directory URLs", "Runtime": "cloudfront-js-2.0"},
                "FunctionCode": code,
            },
        },
        "OriginAccessControl": {
            "Type": "AWS::CloudFront::OriginAccessControl",
            "Properties": {"OriginAccessControlConfig": {
                "Name": name or {"Fn::Sub": "${ProjectName}-private-origin"},
                "OriginAccessControlOriginType": "s3",
                "SigningBehavior": "always",
                "SigningProtocol": "sigv4",
            }},
        },
    }


def upgrade(template, lockdown, redirects=None):
    result = copy.deepcopy(template)
    resources = result["Resources"]
    resources.update(edge_resources(redirects=redirects))
    bucket = resources["WebsiteS3Bucket"]["Properties"]
    if lockdown:
        bucket.pop("AccessControl", None)
        bucket.pop("WebsiteConfiguration", None)
        bucket["OwnershipControls"] = {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]}
        bucket["PublicAccessBlockConfiguration"] = dict.fromkeys(
            ["BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"], True)
        resources.pop("CloudFrontOriginAccessIdentity", None)
    elif bucket.get("AccessControl") == "PublicRead":
        bucket["AccessControl"] = "Private"

    allow_cloudfront = {
        "Sid": "AllowCloudFrontOnly", "Effect": "Allow",
        "Principal": {"Service": "cloudfront.amazonaws.com"}, "Action": "s3:GetObject",
        "Resource": {"Fn::Sub": "arn:${AWS::Partition}:s3:::${WebsiteS3Bucket}/*"},
        "Condition": {"StringEquals": {"AWS:SourceArn": {
            "Fn::Sub": "arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}"}}},
    }
    statements = [allow_cloudfront]
    if not lockdown:
        statements.append({"Sid": "PublicReadDuringCutover", "Effect": "Allow", "Principal": "*",
                           "Action": "s3:GetObject", "Resource": allow_cloudfront["Resource"]})
    resources["WebsiteS3BucketPolicy"]["Properties"]["PolicyDocument"] = {
        "Version": "2012-10-17", "Statement": statements}

    distribution = resources["CloudFrontDistribution"]["Properties"]["DistributionConfig"]
    origin = distribution["Origins"][0]
    origin.pop("CustomOriginConfig", None)
    origin.update({
        "DomainName": {"Fn::GetAtt": ["WebsiteS3Bucket", "RegionalDomainName"]},
        "S3OriginConfig": {"OriginAccessIdentity": ""},
        "OriginAccessControlId": {"Fn::GetAtt": ["OriginAccessControl", "Id"]},
    })
    distribution["DefaultCacheBehavior"]["FunctionAssociations"] = [{
        "EventType": "viewer-request",
        "FunctionARN": {"Fn::GetAtt": ["CleanUrlsFunction", "FunctionMetadata.FunctionARN"]},
    }]
    distribution["CustomErrorResponses"] = [{
        "ErrorCode": code, "ResponseCode": 404, "ResponsePagePath": "/404.html", "ErrorCachingMinTTL": 10,
    } for code in (403, 404)]
    spec = resources["CodeBuildProject"]["Properties"]["Source"]["BuildSpec"]
    resources["CodeBuildProject"]["Properties"]["Source"]["BuildSpec"] = spec.replace(" --acl public-read", "")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--phase", choices=["cutover", "private"], required=True)
    parser.add_argument("--redirects", type=Path)
    args = parser.parse_args()
    redirects = json.loads(args.redirects.read_text()) if args.redirects else {}
    result = upgrade(load_template(args.template), args.phase == "private", redirects)
    args.output.write_text(json.dumps(result, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
