# Clean URL migration rollback

Revert the affected content source commit, push its configured GitHub branch,
and use the standard CodePipeline/CodeBuild deployment, including existing
approval stages. Keep unpublished posts marked `published: false`. Verify
canonical routes, affected assets, and draft exclusion after deployment.

Repair a failed pipeline before publishing. Do not restore content by uploading
local build output or copying website objects outside the pipeline.

Infrastructure rollback belongs in the consuming project's owning CloudFormation
source. Inspect live configuration and reviewed change sets so an update does
not overwrite additional pipeline stages or separately managed resources. Keep
original templates, parameters, and operational receipts in that project's
private infrastructure records, outside this generic package.
