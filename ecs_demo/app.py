#!/usr/bin/env python3

from aws_cdk import (
    aws_ecs_patterns as ecs_patterns,
    aws_ecs as ecs,
    aws_ecr_assets as ecr,
    aws_ec2 as ec2,
    aws_apigateway as apigw,
    core
)

from os import getenv


class PythonService(core.Stack):

    def __init__(self, scope: core.Stack, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create VPC
        self.vpc = ec2.Vpc.from_lookup(
            self, "VPC",
            vpc_name='api-gateway/VPC'
        )

        # Create ECS Cluster
        self.ecs_cluster = ecs.Cluster(
            self, "ECSCluster",
            vpc=self.vpc
        )

        # This high level construct will build a docker image, ecr repo and connect the ecs service to allow pull access
        self.container_image = ecr.DockerImageAsset(
            self, "Image",
            directory="./"
        )

        # Task definition details to define the frontend service container
        self.task_def = ecs_patterns.NetworkLoadBalancedTaskImageOptions(
            image=ecs.ContainerImage.from_ecr_repository(repository=self.container_image.repository),
            container_port=80,
            enable_logging=True,
            environment={
                "GIT_HASH": "12345"
            },
        )

        # Create the frontend service
        self.python_service = ecs_patterns.NetworkLoadBalancedFargateService(
            self, "PythonService",
            cpu=256,
            memory_limit_mib=512,
            cluster=self.ecs_cluster,
            desired_count=1,
            task_image_options=self.task_def,
            public_load_balancer=False,
        )
        
        self.python_service.service.connections.allow_from_any_ipv4(
            port_range=ec2.Port(
                protocol=ec2.Protocol.ALL,
                string_representation="All port 80",
                from_port=80,
            ),
            description="Allows traffic on port 80 from NLB"
        )
        
        # Create VPC Link from API Gateway to NLB
        # TODO: Make api id dynamic
        self.rest_api = apigw.RestApi.from_rest_api_id(
            self, "APIGateway",
            rest_api_id="6znhu1vqp6"
        )
        
        # TODO: Create stage variable for vpc links
        self.gateway_vpc_link = apigw.VpcLink(
            self, "VPCLink",
            description="VPC Link from API Gateway to ECS Python Service",
            targets=[
                self.python_service.load_balancer
            ],
            vpc_link_name="ECS_VPC_LINK"
        )


app = core.App()

# Yes hardcoded, this is just for demo
_env = core.Environment(account='526326026737', region='us-east-2')

PythonService(app, "python-service", env=_env)

app.synth()

