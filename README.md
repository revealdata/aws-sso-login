# AWS SSO Login Manager

## Description
The AWS Login manager simplifies session management for AWS SSO.

## Features
- Allows you to login to multiple AWS SSO accounts and roles with a single command.
- Optionally authorize docker with AWS credentials for each AWS profile using AWS SSO.
- Optionally Authorize kubeconfig for EKS with AWS credentials for each AWS profile using AWS SSO.
- Optionally authorize a CodeArtifact domain with AWS credentials for each AWS profile using AWS SSO.

## [Releases](https://github.com/revealdata/aws-sso-login/releases/latest)
Each release version builds a portable executable for each of the following operaing systems
1. Linux (AMD64) `aws-sso-login-linux-amd64.zip`
1. Mac OS (AMD54) `aws-sso-login-macos-amd64.dmg` - Tested as working on Apple Silicon/M1.
1. Windows `aws-sso-login.exe`

### MacOS Release
The MacOS release includes both a command-line binary and a `.app` version. The app version can be used as a standard Application when running without any command-line arguments. 

You can use the keyboard shortcut: **Control+Shift+Command+T** in Finder to add the application to the Mac Dock.

If you run the application you may receive one the following errors:
- `aws-sso-login.app cannot be opened because the developer cannot be verified.`

  To resolve this error, open your System Settings and select the Privacy tab. There you will see a list of applications that require authorization. Click the "Allow" button next to the `aws-sso-login.app` entry.
- `aws-sso-login.app is damaged and cannot be opened.`

  To resolve this error, open a terminal and run the following command: 
  ```
  xattr -d com.apple.quarantine /Applications/aws-sso-login.app
  ```

### Linux Release
The Linux release cannot be used with Windows subsystem for Linux. The application needs to spawn a browser session which does not translate from WSL to Windows.


## Usage
```
aws-login-manager.py
```

The script will attempt to locate the following application in your path (each can be specified using command arguments):
- `aws`
- `docker`
- `kubectl`

If the application is not found in your path, that feature will be disabled. If `aws` is not found, the appplication will not run.

## Configuration
The script will attempt to locate the following configuration files in your path (each can be specified using command arguments):
- `${HOME}/.aws/config` (AWS CLI configuration)
- `${HOME}/.eks_auth` (EKS configuration - See **EKS Configuration** below)

### AWS CLI Configuration
The AWS CLI configuration fields are mostly standard and should not be modified unless you know what you are doing.
The following fields can be added specifically for `aws-sso-login`:
 - `aws_sso_login`: (true|false). If set to false, the profile will be ignored by `aws-sso-login`.If this field does not
    exist, then the profile will be considered enabled.
   - example:  `aws_sso_login = false`
 - `code_artifact_domain`: If a CodeArtifact domain names is set, The option of getting a CodeArtifact authorization token will be enabled. 
    The token must be copied into a terminal session and used as a variable in commands that use CodeArtifact (`pip`, `npm`, `maven`, etc.)
   - example: `code_artifact_domain = my-codeartifact-domain`
 
 The following is an example AWS CLI configuration section:
```ini
[profile default]
sso_start_url = https://my-sso-domain.awsapps.com/start
sso_region = us-east-1
sso_account_id = 083387868364
sso_role_name = Department-Dev
code_artifact_domain = my-codeartifact-domain
region = us-east-1
output = json
```

### EKS Configuration
This script utilizes a configuration file to specify the EKS clusters and roles to authorize. The configuration file is `ini` format similar to the AWS CLI configuration file. 

Each section of the configuration file represents a cluster. The section name is the name of the kube context. The section contains the following keys:
 - `ENABLE`: (optional) If set to `0` or `false` the cluster will be skipped. Default is `true`.
 - `EKS_CLUSTER`: (required) The name of the EKS cluster.
 - `AWS_PROFILE`: (required) The name of the AWS profile to use for the cluster authentication.
 - `AWS_REGION`: (optional) The AWS region of the EKS cluster. If not specified the region will be determined from the AWS CLI configuration file.
 - `AWS_PARTITION`: (optional) The AWS partition. Defaults to `aws` if not specified. Used to build the arn for the `ROLE`.
 - `ROLE`: (optional) The name of the AWS role to assume for the cluster authentication. If not specified, no role will be used.
 - `KUBE_CONFIG`: (optional) The path to the kubeconfig file to update. If not specified, the default kubeconfig file will be used.

The following is an example cluster configuration section:
```ini
[prod-us]
ENABLE=true
EKS_CLUSTER=prod-eks-cluster-name
AWS_PROFILE=default
AWS_REGION=us-east-1
AWS_PARTITION=aws
ROLE=Department-Dev
KUBE_CONFIG=~/.kube/config.prod
```
