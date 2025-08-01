import os
import sys
import subprocess
import shlex
import platform
import fileinput
from pathlib import Path
from configparser import ConfigParser

class Argument():
    def __init__(self,
            label, help,
            value=None, enabled=True,
            options=[], url=None, bin=None,
            stop_options=None, stop_run=False,
            verification={},
            total=None
        ):
        self.label = label
        self.help = help
        self.value = value
        self.url = url
        self.bin = bin
        self.enabled = enabled
        self.options = options
        self.total = total
        self.stop_options = stop_options
        self.stop_run = stop_run
        self.verification = verification
        self.errors = []

class AwsProfile:
    def __init__(self, aws_config, section):
        self.config_attrs = (
            'region',
            'sso_region',
            'source_profile',
            'role_arn',
            'sso_account_id',
            'sso_role_name',
            'sso_start_url',
            'code_artifact_domain',
            'code_artifact_env_file'
        )
        self.section = section
        self.ecr_password = None
        self.enabled = True
        self.code_artifact_domain = None
        self.code_artifact_env_file = None
        aws_sso_login = self.__get_config_attribute__(aws_config, "aws_sso_login")
        if aws_sso_login:
            self.enabled = self.__str_to_bool__(aws_sso_login)

        self.name = section[8:] if section.startswith('profile ') else section
        # Load the aws config attributes
        for attr in self.config_attrs:
            # print(f"[{self.name}] Setting {attr} = {self.__get_config_attribute__(aws_config, attr)}")
            setattr(self, attr, self.__get_config_attribute__(aws_config, attr))

    def __str_to_bool__(self, value):
        """ Convert a string to a boolean value """
        return value.lower() in ("yes", "true", "t", "1")
    def __get_config_attribute__(self, aws_config, attr: str):
        """ Get the value of an attribute from the aws config file """
        try:
            return aws_config.get(self.section, attr)
        except Exception:
            return None

class KubeConfig:
    def __init__(self, eks_config, section):
        self.config_attrs = ('ENABLE', 'AWS_REGION', 'EKS_CLUSTER', 'AWS_PROFILE', 'AWS_PARTITION', 'ROLE', 'KUBE_CONFIG')
        self.context = section
        self.aws_profile = None
        self.aws_partition = "aws"
        self.enable = False
        self.kube_config = f"{Path.home()}{os.sep}.kube{os.sep}config"
        # Load the aws config attributes
        for attr in self.config_attrs:
            value = self.__get_config_attribute__(eks_config, attr)
            if value:
                setattr(self, attr.lower(), value)

        if hasattr(self, "enable"):
            self.enable = self.__str_to_bool__(self.enable)
        else:
            self.enable = True

    def __get_config_attribute__(self, eks_config, attr: str):
        """ Get the value of an attribute from the eks_auth config file """
        try:
            return eks_config.get(self.context, attr).lower()
        except Exception:
            return None

    def __str_to_bool__(self, str):
        if not str:
            return False
        if str.lower() in ['1', 'true']:
            return True
        else:
            return False

class Initialize:
    def __init__(self, arguments):
        self.arguments = arguments
        self.aws_config = None
        self.eks_config = None
        self.profiles = {}
        self.kube_configs = {}
        self.system = f"{platform.system()}".lower()
        # Search path for dependant binaries (aws, kubectl, docker)
        if self.system == "darwin" and getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.search_paths = [
                '/usr/local/bin',
                '/usr/bin',
                '/bin',
                '/usr/sbin',
                '/sbin',
                '/opt/homebrew/bin',
                f"{Path.home()}{os.sep}bin",
                f"{Path.home()}{os.sep}.rd{os.sep}bin"
            ]
        else:
            path = os.environ.get('PATH', '')
            self.search_paths = path.split(os.pathsep)

        # Verify that shell commands are installed
        for cmd in self.arguments["cmd"]:
            self.arguments["cmd"][cmd].value = self.__bin_search__(self.arguments["cmd"][cmd].bin)
            if not self.arguments["cmd"][cmd].value or not os.path.isfile(self.arguments["cmd"][cmd].value):
                msg_type = "ERROR" if self.arguments["cmd"][cmd].stop_run else "WARNING"
                self.arguments["cmd"][cmd].errors.append(f"[{msg_type}] Command file: {self.arguments['cmd'][cmd].bin}, not found. {cmd} will be disabled.")
                self.arguments["cmd"][cmd].errors.append(f"[HELP] See <a href='{self.arguments['cmd'][cmd].url}'>{self.arguments['cmd'][cmd].url}</a> for more information.")
                for option in self.arguments["cmd"][cmd].stop_options:
                    self.arguments["options"][option].enabled = False

        self.__init_eks_auth__()

        # Create parsers for the configuration files
        if self.arguments["config"]["awscli"].enabled:
            self.aws_config = ConfigParser()
            self.aws_config.read(os.path.expanduser(self.arguments["config"]["awscli"].value))
        if self.arguments["config"]["eks"].enabled:
            self.eks_config = ConfigParser()
            self.eks_config.read(os.path.expanduser(self.arguments["config"]["eks"].value))

        # Create a dictionary of profiles
        if self.aws_config:
            for section in self.aws_config.sections():
                profile = AwsProfile(self.aws_config, section)

                if profile.sso_start_url and profile.enabled:
                    # If any of the profiles contains code_artifact_domain, enable the cart option
                    if profile.code_artifact_domain:
                        self.arguments["options"]["do_cart"].total += 1
                        self.arguments["options"]["do_cart"].value = True
                        # print(f"Found code_artifact_domain in profile: {profile.name}. total: {self.arguments['options']['do_cart'].total}")

                    self.profiles[profile.name] = profile
            self.arguments["options"]["do_login"].total = len(self.profiles)

        # Create a dictionary of EKS clusters
        if self.eks_config:
            for section in self.eks_config.sections():
                kube_config = KubeConfig(self.eks_config, section)
                if kube_config.enable:
                    # Add the AWS Profile to the EKS cluster Config
                    if kube_config.aws_profile and kube_config.aws_profile in self.profiles:
                        kube_config.aws_profile = self.profiles[kube_config.aws_profile]
                    self.kube_configs[kube_config.context] = kube_config
            self.arguments["options"]["do_eks"].total = len(self.kube_configs)

    def __bin_search__(self, cmd):
        try:
            self.search_paths.extend(os.environ["PATH"].split(os.pathsep))
        except Exception:
            pass
        # remove duplicates
        self.search_paths = list(dict.fromkeys(self.search_paths))
        bin_path = None
        if self.system == "windows":
            cmd = f"{cmd}.exe"
        for path in self.search_paths:
            if os.path.isfile(f"{path}{os.sep}{cmd}"):
                bin_path = f"{path}{os.sep}{cmd}"
                break
        return bin_path

    def __init_eks_auth__(self):
        """ Initialize the EKS config file """
        if not os.path.isfile(self.arguments["config"]["eks"].value):
            self.arguments["config"]["eks"].errors.append("[WARNING] EKS Config file not found. Creating...")
            try:
                with open(self.arguments["config"]["eks"].value, 'w') as f:
                    f.write(f"""
[DEFAULT]
## Configuration file for eks_auth function ##
## Example:
#[KUBE_CONTEXT]
#ENABLE=true
#EKS_CLUSTER=my-cluster
#AWS_PROFILE=default
#AWS_REGION=us-east-1
#AWS_PARTITION=aws
#ROLE=kubernetes-admins-access
""")
                return True
            except Exception as e:
                self.arguments["config"]["eks"]["errors"].append("[ERROR] Error creating EKS config file: {}".format(e))
                self.arguments["config"]["eks"].enabled = False
                return False


class EnvCodeArtifactToken:
    def __init__(self, token, domain, env_file=None):
        self.var_header = '# CodeArtifact Token'
        self.var_footer = '# End CodeArtifact Token'
        self.var_domain = ['CODEARTIFACT_DOMAIN', domain]
        self.var_token = ['CODEARTIFACT_AUTH_TOKEN', token]
        self.shell_rc = None
        self.env_content = None
        self.env_file_override = False
        self.written = False
        self.is_ps = True if "WINDIR" in os.environ.keys() else False

        # Create a default env file path if not specified in the profile
        if not env_file and "SHELL" in os.environ.keys():
            # Create a default env file path for Linux/MacOS
            self.shell_rc = f"{Path.home()}{os.sep}.{os.environ['SHELL'].split('/')[-1]}rc"
        elif not env_file and self.is_ps:
            self.is_ps = True
            # Create a default env file path for Windows
            pspaths = os.environ.get('PSMODULEPATH').split(';')
            for pspath in pspaths:
                if os.environ.get('HOMEPATH') in pspath:
                    self.shell_rc = pspath.replace('Modules', 'Microsoft.PowerShell_profile.ps1')
                    break
        else:
            if os.path.isdir(os.path.dirname(os.path.realpath(env_file))):
                self.env_file_override = True
                self.shell_rc = os.path.realpath(env_file)

        if self.shell_rc:
            self.written = self.__write_token__()

    def __format_env_line__(self, env_data: list):
        """ Format the environment variable line """
        if not isinstance(env_data, list) or len(env_data) < 2:
            return None

        if not self.is_ps:
            return f"export {env_data[0]}='{env_data[1]}'"
        else:
            return f"$env:{env_data[0]} = '{env_data[1]}'"

    def __write_token__(self):
        """ Write the token to the shell rc file """
        # Generate the variable set lines
        var_domain = self.__format_env_line__(self.var_domain)
        var_token = self.__format_env_line__(self.var_token)
        # print(f"domain: {var_domain}")
        # print(f"token: {var_token}")

        # If the file does not exist, create it
        if not os.path.isfile(self.shell_rc):
            # print(f"Creating {self.shell_rc}")
            with open(self.shell_rc, 'w') as f:
                f.write(f"{self.var_header}\n")
                f.write(f"{var_domain}\n")
                f.write(f"{var_token}\n")
                f.write(f"{self.var_footer}\n")
            return True
        else:
            # If the file exists, check if the token is already in the file
            replace = False
            with open(self.shell_rc, 'r') as f:
                if self.var_header in f.read():
                    replace = True
            if replace:
                # Replace the existing token
                # print(f"Replacing token in {self.shell_rc}")
                for line in fileinput.input(self.shell_rc, inplace=True):
                    if self.var_header in line:
                        print(self.var_header, end='\n')
                    elif self.var_domain[0] in line:
                        print(var_domain)
                    elif self.var_token[0] in line:
                        print(var_token)
                    elif self.var_footer in line:
                        print(self.var_footer, end='\n')
                    else:
                        print(line, end='')
                return True
            else:
                # Append the token to the file
                # print(f"Appending token to {self.shell_rc}")
                with open(self.shell_rc, 'a') as f:
                    f.write(f"\n{self.var_header}\n")
                    f.write(f"{var_domain}\n")
                    f.write(f"{var_token}\n")
                    f.write(f"{self.var_footer}\n")
                return True
