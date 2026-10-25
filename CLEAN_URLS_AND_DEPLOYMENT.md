# Clean URLs and pipeline deployments

## Routing contract

Jekyll emits each canonical page as `<path>/index.html`, and its public URL ends
in `/`. CloudFront redirects a missing trailing slash, removes an explicit
`index.html`, and internally resolves directory indexes. Real files pass through.

| Request | Response |
| --- | --- |
| `/posts/example/` | Fetch `/posts/example/index.html` |
| `/posts/example` | 301 to `/posts/example/` |
| `/posts/example/index.html` | 301 to `/posts/example/` |
| `/index.html` | 301 to `/` |
| `/css/style.css` | Serve the asset |
| `/assets/example-image` | Serve the extensionless asset |
| `/missing-page/` | Site `404.html`, HTTP 404 |

Redirects preserve encoded, empty, and repeated query values. Redirect targets
stay on the same host, including for malformed paths with multiple leading
slashes. Asset prefixes `/assets/`, `/css/`, and `/images/` bypass page routing.
Other extensionless resources need an explicit routing policy in the consuming
project; the generic function cannot infer their existence.

Arbitrary `.html` files remain addressable. Only declared historical mappings
redirect to new canonical URLs; the function does not guess between an HTML file
and a directory index.

## Site source configuration

Choose a trailing-slash permalink pattern in the consuming Jekyll repository:

```yaml
permalink: /:year/:month/:day/:title/
```

Explicit page and post permalinks must follow the same contract. Generate
canonical metadata and internal links from `page.url` and the configured public
base URL. Set an explicit timezone when dated URLs must be stable across build
environments. Configure Jekyll plugins and exclusions in that repository.

Keep unpublished posts in source with `published: false`. The normal Jekyll build
excludes them; deployments must not enable `--unpublished` or another draft flag.

Historical redirect mappings belong to the consuming project. The migration
renderer accepts a JSON object such as:

```json
{"/archive/example.html": "/posts/example/"}
```

These entries produce query-preserving HTTP 301 responses. They are distinct
from HTML compatibility documents, which can use meta refresh but normally
return HTTP 200. Exclude compatibility documents from canonical sitemaps.

## Private origin

The template uses an S3 REST origin with CloudFront Origin Access Control:

- Always-signed requests from CloudFront to S3.
- Bucket-owner-enforced object ownership and all public-access blocks enabled.
- A bucket policy allowing the CloudFront service principal, scoped to the
  distribution ARN.
- No S3 website hosting or public object ACLs.
- CloudFront maps origin 403 and 404 responses to `/404.html` with HTTP 404.

A private S3 origin can return 403 for a missing object, so both origin error
codes need the HTML error mapping. CodeBuild uploads without public ACL flags.

## Existing-stack migration

Inspect the current stack template and live resource configuration before
preparing an update. Generic package defaults must not overwrite additional
stages, approval actions, bucket overrides, or separately managed resources in a
consuming deployment. Resolve drift in the owning infrastructure source.

Render changes onto the existing template:

```sh
python3 scripts/migration.py current-template.yml cutover.json --phase cutover --redirects redirects.json
python3 scripts/migration.py current-template.yml private.json --phase private --redirects redirects.json
```

The renderer preserves existing intrinsic expressions and unrelated resources.
The cutover phase retains public reads while CloudFront begins using OAC; the
private phase removes website hosting and public origin access. Review each
CloudFormation change set before applying it. Keep deployment-specific templates,
parameter records, hostnames, credentials, and execution receipts outside this
public package, in the consuming project's private infrastructure source.

## Content deployment

```text
commit(source, draft_flags) -> push(configured_branch)
GitHub_webhook -> CodePipeline_source -> CodeBuild_Jekyll_build
existing_approval_stages -> CodeBuild_S3_sync -> CodeBuild_CloudFront_invalidation
verify(canonical_routes, affected_assets, draft_exclusion)
```

Use the existing pipeline for publication. A source-connection or build failure
must be repaired in the pipeline; it does not justify uploading a local build or
invalidating CloudFront directly. Preserve existing development and approval
stages. Roll content back by reverting the source commit and deploying the revert
through the same pipeline.

## Validation

Run the package checks:

```sh
node --test test/clean-urls.test.cjs
python3 -m unittest discover -s test -p 'test_*.py'
```

After the consuming pipeline completes, verify canonical redirects, directory
access, declared historical URLs, affected assets, query preservation, HTML 404s,
and denied direct S3 access. Confirm that unpublished post routes remain absent.
Build, deployment, and live verification are separate evidence; package tests
alone do not establish the state of a deployed site.
