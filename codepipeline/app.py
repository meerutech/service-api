#!/usr/bin/env python3

from aws_cdk import (
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_secretsmanager as secretsmgr, 
    aws_codebuild as codebuild,
    aws_iam as iam,
    core
)

from configparser import ConfigParser
from os import getenv

config = ConfigParser()
config.read('../config.ini')


class CodeBuildProjects(core.Construct):

    def __init__(self, scope: core.Construct, id: str, buildspec, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.buildspec = buildspec
        self.build_image = codebuild.LinuxBuildImage.STANDARD_2_0
        
        self.project = codebuild.PipelineProject(
            self, "Project",
            environment=codebuild.BuildEnvironment(
                build_image=self.build_image,
                privileged=True
            ),
            build_spec=codebuild.BuildSpec.from_source_filename(self.buildspec),
            environment_variables={
                'REPO_NAME': codebuild.BuildEnvironmentVariable(value=config['CODEPIPELINE']['GITHUB_REPO'])
            },
        )
        
        # TODO: Don't need admin, let's make this least privilege
        self.admin_policy = iam.Policy(
            self, "AdminPolicy",
            roles=[self.project.role],
            statements=[
                iam.PolicyStatement(
                    actions=['*'],
                    resources=['*'],
                )
            ]
        )
        

class ServiceAPIPipeline(core.Stack):

    def __init__(self, scope: core.Stack, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # create a pipeline
        self.pipeline = codepipeline.Pipeline(self, "Pipeline", pipeline_name='Service_API')
        
        # add a source stage
        self.source_stage = self.pipeline.add_stage(stage_name="Source")
        self.source_artifact = codepipeline.Artifact()
        
        # codebuild projects
        self.codebuild_deploy_swagger = CodeBuildProjects(self, "CodebuildSwagger", buildspec='buildspec-swagger.yml')
        self.codebuild_deploy_ecr = CodeBuildProjects(self, "CodebuildDocker", buildspec='buildspec-docker.yml')
        
        # add source action
        self.source_stage.add_action(codepipeline_actions.GitHubSourceAction(
            oauth_token=core.SecretValue.secrets_manager(secret_id='prod/github_oauth_token',json_field='github_oauth_token'),
            output=self.source_artifact,
            owner=config['CODEPIPELINE']['GITHUB_OWNER'],
            repo=config['CODEPIPELINE']['GITHUB_REPO'],
            action_name='Pull_Source',
            run_order=1,
        ))
        
        # add build/test stage
        self.deploy_stage = self.pipeline.add_stage(stage_name='Test_and_Build')
        
        # add build/test codebuild action
        self.deploy_stage.add_action(codepipeline_actions.CodeBuildAction(
            input=self.source_artifact,
            project=self.codebuild_deploy_ecr.project,
            action_name='Test_and_Build'
        ))
        
        # add deploy stage
        self.deploy_stage = self.pipeline.add_stage(stage_name='API_Deployment')
        
        # add deploy codebuild action
        self.deploy_stage.add_action(codepipeline_actions.CodeBuildAction(
            input=self.source_artifact,
            project=self.codebuild_deploy_swagger.project,
            action_name='API_Deployment'
        ))
        
        
app = core.App()

_env = core.Environment(account=config['CODEPIPELINE']['CDK_DEFAULT_ACCOUNT'], region=config['CODEPIPELINE']['AWS_DEFAULT_REGION'])

ServiceAPIPipeline(app, "service-api-build-deploy-pipeline", env=_env)

app.synth()
