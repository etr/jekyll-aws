import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("migration", ROOT / "scripts/migration.py")
if SPEC and SPEC.loader and SPEC.origin and pathlib.Path(SPEC.origin).exists():
    migration = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(migration)
else:
    migration = None


class MigrationTests(unittest.TestCase):
    def test_existing_getatt_syntax_is_preserved(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "template.yml"
            path.write_text("Value: !GetAtt CodePipelineRole.Arn\n")
            self.assertEqual(migration.load_template(path), {"Value": {"Fn::GetAtt": "CodePipelineRole.Arn"}})

    def setUp(self):
        self.assertIsNotNone(migration, "migration template renderer is required")
        self.template = migration.load_template(ROOT / "cloudformation.yml")

    def test_cutover_keeps_public_read_until_oac_is_serving(self):
        upgraded = migration.upgrade(self.template, lockdown=False)
        statements = upgraded["Resources"]["WebsiteS3BucketPolicy"]["Properties"]["PolicyDocument"]["Statement"]
        self.assertTrue(any(s.get("Principal") == "*" for s in statements))
        self.assertTrue(any(s.get("Principal") == {"Service": "cloudfront.amazonaws.com"} for s in statements))

    def test_lockdown_removes_public_access_and_website_origin(self):
        upgraded = migration.upgrade(self.template, lockdown=True)
        resources = upgraded["Resources"]
        bucket = resources["WebsiteS3Bucket"]["Properties"]
        self.assertTrue(all(bucket["PublicAccessBlockConfiguration"].values()))
        self.assertNotIn("WebsiteConfiguration", bucket)
        statements = resources["WebsiteS3BucketPolicy"]["Properties"]["PolicyDocument"]["Statement"]
        self.assertFalse(any(s.get("Principal") == "*" for s in statements))
        self.assertEqual(statements[0]["Condition"]["StringEquals"]["AWS:SourceArn"],
                         {"Fn::Sub": "arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}"})

    def test_routing_and_error_mapping_are_attached_to_rest_origin(self):
        upgraded = migration.upgrade(self.template, lockdown=True)
        config = upgraded["Resources"]["CloudFrontDistribution"]["Properties"]["DistributionConfig"]
        origin = config["Origins"][0]
        self.assertIn("S3OriginConfig", origin)
        self.assertNotIn("CustomOriginConfig", origin)
        self.assertEqual(origin["DomainName"], {"Fn::GetAtt": ["WebsiteS3Bucket", "RegionalDomainName"]})
        self.assertEqual(config["DefaultCacheBehavior"]["FunctionAssociations"][0]["EventType"], "viewer-request")
        self.assertEqual([(x["ErrorCode"], x["ResponseCode"]) for x in config["CustomErrorResponses"]], [(403, 404), (404, 404)])

    def test_pipeline_stops_sending_public_acls(self):
        upgraded = migration.upgrade(self.template, lockdown=True)
        spec = upgraded["Resources"]["CodeBuildProject"]["Properties"]["Source"]["BuildSpec"]
        self.assertNotIn("--acl public-read", spec)
        self.assertNotIn("--unpublished", spec)


if __name__ == "__main__":
    unittest.main()
