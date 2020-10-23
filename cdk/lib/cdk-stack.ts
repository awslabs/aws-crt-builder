import * as cdk from '@aws-cdk/core';
import * as codepipeline from '@aws-cdk/aws-codepipeline';
import * as codepipeline_actions from '@aws-cdk/aws-codepipeline-actions';
import * as s3 from '@aws-cdk/aws-s3';
import * as codebuild from '@aws-cdk/aws-codebuild';


export class ReleasePipelineStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const sourceArtifact = new codepipeline.Artifact();
    const pipeline = new codepipeline.Pipeline(this, 'TestReleasePipeline', {
      stages: [
        {
          stageName: 'Source',
          actions: [
            new codepipeline_actions.GitHubSourceAction({
              actionName: 'GitHubSourceTag',
              owner: 'awslabs',
              repo: 'aws-crt-builder',
              oauthToken: cdk.SecretValue.secretsManager('github/token'),
              output: sourceArtifact,
              branch: 'master',
            })
          ]
        },
        {
          stageName: 'VersionCheck',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'VersionCheck',
              input: sourceArtifact,
              project: new codebuild.PipelineProject(this, 'VersionCheckProject', {

              })
            })
          ]
        }
      ]
    });

  }
}
