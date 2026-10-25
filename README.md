# jekyll-aws

Automatically deploy your GitHub-hosted Jekyll project on AWS with your own custom domain via S3, CloudFront, and Route53.  

CI/CD is also included to automatically deploy when you push your Jekyll changes to GitHub.  

Deploy blog content only through the existing GitHub → CodePipeline → CodeBuild
path. Commit source changes and push the configured branch; complete any
existing pipeline approval stage. Draft posts use `published: false`, and the
normal Jekyll build excludes them. Do not deploy local `_site` output, upload
replacement website objects, or invalidate CloudFront outside the pipeline.
Roll content back by reverting the source commit and deploying that revision
through the same pipeline. Repair source integration failures before deploying;
they do not justify a direct-upload fallback.

Pages use trailing-slash URLs backed by `<path>/index.html`. CloudFront normalizes
directory URLs, preserves query strings, and serves the site's `404.html` with
status 404. The S3 REST origin is private behind Origin Access Control.

For existing stacks, follow [the migration guide](CLEAN_URLS_AND_DEPLOYMENT.md).
Render changes onto the
stack's actual template rather than replacing a drifted deployment with this
repository's template:

```sh
python3 scripts/migration.py current-template.yml cutover.json --phase cutover
python3 scripts/migration.py current-template.yml private.json --phase private
```

Review CloudFormation change sets, verify the cutover, then apply the private
phase. Optional `--redirects <site-owned-json>` supplies exact historical URL
mappings; arbitrary `.html` files remain addressable. The renderer requires
PyYAML. Routing tests run with `node --test test/clean-urls.test.cjs`; template
tests run with `python3 -m unittest discover -s test -p 'test_*.py'`.

Existing stacks can differ from the generic template. Keep deployment-specific
templates and operational records in a private infrastructure repository.
Preserve resource ownership and existing development/approval stages when
repairing credentials. Credential values are CloudFormation parameters and
must not be stored in source control.

Requires a GitHub Jekyll project, a GitHub personal access token, an AWS account, and a Route53-purchased domain.

Associated blog post can be found [here](https://ethanfahy.cloud/2019/09/24/jekyll-aws.html).

## Architecture

![jekyll-aws architecture](architecture-diagram.png)

The diagram above shows a non-exhaustive architecture overview (e.g. S3 log bucket, IAM Roles created in `cloudformation.html` are not shown).

## Instructions

- You need an AWS account, and you need to be able to log in with sufficient permissions to create all of the AWS Resources contained in `cloudformation.yml`.
- You need to register your desired domain using AWS Route53 in advance of using `cloudformation.yml`.
- You need a public certificate for your domain to be used by AWS CloudFront. Follow the instructions on the [AWS Docs](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html).
- You need a GitHub account that contains a repository with a Jekyll project.  Note that if your Jekyll project uses CoffeeScript you'll need to edit the `BuildSpec` parameter in the template so that NodeJS gets installed (see some of the blog posts in the Acknowledgements for an example of how this is done).
- You need to [create a GitHub personal access token](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line) with the `repo` and `admin:repo_hook` options selected for CodePipeline to access your repository ([AWS Docs](https://docs.aws.amazon.com/codepipeline/latest/userguide/GitHub-create-personal-token-CLI.html)).
- Once you have all the above prerequisites in order, you simply create an AWS CloudFormation stack using the `cloudformation.yml` file in this project and fill in all of the required parameters.  Once the template has been deployed successfully, CodeBuild will build and deploy your website automatically and you should see it hosted at the domain that you specified in your `WebsiteURL` parameter in the CloudFormation stack.  You will see your website changes automatically whenever you push changes to your GitHub Jekyll repository on the specified branch.  

## Why does this project exist?

There exist several blog posts online (see the Acknowlegements section below) that outline how to deploy a Jekyll website to AWS, but I wanted to codify the entire process into a single CloudFormation script so that I could better manage my own [personal website](https://ethanfahy.cloud).  I also wanted to provide an easier out-of-the-box solution to anyone looking to host their Jekyll site on AWS.

## Acknowledgements

In the course of building this CloudFormation template I referenced several blogs and AWS support pages, notably:

- [AWS tutorial for wiring up GitHub to CodePipeline via CloudFormation](https://docs.aws.amazon.com/codepipeline/latest/userguide/tutorials-cloudformation-github.html)
- [Zeta Two blog post about deploying Jekyll to AWS similar to how it's done in this project](https://zeta-two.com/software/2018/07/09/static-website-s3-codepipeline.html)
- [Alex Bilbie blog post about deploying Jekyll to AWS similar to how it's done in this project](https://alexbilbie.com/2016/12/codebuild-codepipeline-update-jekyll-website/)
- [Joeri Smits blog post about deploying Jekyll to AWS similar to how it's done in this project](https://joerismits.nl/blog/deploy-a-serverless-jekyll-website-on-a-cdn-at-aws/)
- [AWS blog post about using OAI to only allow website traffic to CloudFront and not to S3 while also using Lambda@Edge to handle paths that end in / and not /index.html](https://aws.amazon.com/blogs/compute/implementing-default-directory-indexes-in-amazon-s3-backed-amazon-cloudfront-origins-using-lambdaedge/)

Thanks to the authors above without whom I don't think I could have done this project successfully.
