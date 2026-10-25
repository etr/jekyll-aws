# Clean URL migration checklist

- Inspect the current deployed template, origins, policies, and pipeline stages.
- Keep deployment-specific records in the consuming project's private source.
- Verify the Jekyll directory-index contract and `published: false` draft flags.
- Run package routing and template tests.
- Review CloudFormation change sets and preserve existing pipeline stages.
- Deploy content through the configured CodePipeline/CodeBuild pipeline.
- Verify canonical routes, legacy mappings, assets, query values, and HTML 404s.
- Verify direct S3 denial after the private-origin phase.
- Verify that unpublished post routes remain absent.

See [the migration guide](../../CLEAN_URLS_AND_DEPLOYMENT.md) and
[rollback guidance](clean-urls-rollback.md). This package records generic behavior;
execution status belongs to the consuming deployment.
