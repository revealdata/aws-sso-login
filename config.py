import os
from pathlib import Path
from lib.classes import Argument

APP = {
    'name': 'aws-sso-login',
    'description': 'AWS SSO Login Manager',
    'version': '1.2.5',
    'author': 'Russ Cook <rcook@revealdata.com>',
    'url': 'https://github.com/revealdata/aws-sso-login'
}

ARGUMENTS = {
    "config": {
        "awscli": Argument(
            label="aws config",
            help="Path to 'aws' config file.",
            value=f"{Path.home()}{os.sep}.aws{os.sep}config",
            stop_options=["do_login", "do_eks", "do_ecr"]
        ),
        "eks": Argument(
            label="eks config",
            help="Path to 'eks_auth' config file.",
            value=f"{Path.home()}{os.sep}.eks_auth",
            stop_options=["do_eks"]
        ),
    },
    "cmd": {
        "awscli": Argument(
            label="aws binary",
            help="Path to 'aws' binary.",
            bin="aws",
            stop_options=["do_login", "do_eks", "do_ecr"],
            stop_run=True,
            url="https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html",
            verification={"version": {"args": "--version", "regex": "aws-cli/(.*)"}}
        ),
        "kubectl": Argument(
            label="kubectl binary",
            help="Path to 'kubectl' binary.",
            bin="kubectl",
            stop_options=["do_eks"],
            url="https://kubernetes.io/docs/tasks/tools/install-kubectl/",
            verification={"version": {"args": "version --client", "regex": "Client Version: v(.*)"}},
        ),
        "docker": Argument(
            label="docker binary",
            help="Path to 'docker' binary.",
            bin="docker",
            stop_options=["do_ecr"],
            url="https://docs.docker.com/get-docker/",
            verification={"version": {"args": "--version", "regex": ""}, "alive": {"args": "ps"}}

        ),
    },
    "options": {
        "do_login": Argument(label="AWS SSO Login", help="Skip login to AWS SSO.", enabled=True, value=True, total=0),
        "do_eks": Argument(label="AWS EKS Auth", help="Skip EKS authorization.", enabled=True, value=True, total=0),
        "do_ecr": Argument(label="AWS ECR Auth", help="Login to AWS ECR. (requires docker)", enabled=True, value=False),
        "do_cart": Argument(label="AWS CodeArtifact", help="Get AWS CodeArtifact Auth Token.", enabled=True, value=False, total=0),
    }
}
