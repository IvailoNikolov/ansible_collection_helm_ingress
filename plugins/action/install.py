from ansible.plugins.action import ActionBase
import copy
from ansible.errors import (
    AnsibleError,
    AnsibleFileNotFound,
    AnsibleAction,
    AnsibleActionFail,
)
import re
import requests
import yaml


def validate_helm_package(packages_info):
    # retrieve package information

    repo = packages_info.get('chart_repo_url')
    package_name = packages_info.get('chart_ref')
    version = packages_info.get('chart_version')

    r_release_name = requests.get(f'{repo}/index.yaml')
    r_last_release_name_yaml = yaml.safe_load(r_release_name.content)
    package_existing_version = r_last_release_name_yaml.get('entries',{}).get(package_name,"")

    is_package_version_valid = any([
        existing_version.get('version') == version
        for existing_version in package_existing_version 
    ])

    if not is_package_version_valid and package_existing_version:
        version = package_existing_version[0].get('version')

    packages_info['chart_version']=version

    return packages_info

class ActionModule(ActionBase):

    # copy of kubernetes core get_kubeconfig
    def get_kubeconfig(self, kubeconfig, remote_transport, new_module_args):
        if isinstance(kubeconfig, str):
            # find the kubeconfig in the expected search path
            if not remote_transport:
                # kubeconfig is local
                # find in expected paths
                configs = []
                for config in kubeconfig.split(ENV_KUBECONFIG_PATH_SEPARATOR):
                    config = self._find_needle("files", config)

                    # decrypt kubeconfig found
                    configs.append(self._loader.get_real_file(config, decrypt=True))
                new_module_args["kubeconfig"] = ENV_KUBECONFIG_PATH_SEPARATOR.join(
                    configs
                )

    def _ensure_invocation(self, result):
        # NOTE: adding invocation arguments here needs to be kept in sync with
        # any no_log specified in the argument_spec in the module.
        if "invocation" not in result:
            if self._play_context.no_log:
                result["invocation"] = "CENSORED: no_log is set"
            else:
                result["invocation"] = self._task.args.copy()
                result["invocation"]["module_args"] = self._task.args.copy()

        return result

    def remove_helm_secret(self,module_args,task_vars):
        
        k8s_info = self._execute_module(
            module_name="kubernetes.core.k8s_info",
            module_args={
                'api_version': 'v1',
                'kind': 'Secret',
                'namespace':module_args['release_namespace'],
                'kubeconfig':module_args['kubeconfig'],
                'context':module_args['context'],
                'validate_certs': module_args['validate_certs']
            },
            task_vars=task_vars,
        )
        module_name = module_args['name']
        regex_match = f'sh.helm.release.v1.{module_name}.*'
        secret_to_delete = [
            secret['metadata']['name']
            for secret in k8s_info['resources']
            if re.match(regex_match,secret['metadata']['name'] )
        ]


        for secret in secret_to_delete:
            k8s_info = self._execute_module(
                module_name="kubernetes.core.k8s",
                module_args={
                    'state': 'absent',
                    'api_version': 'v1',
                    'kind': 'Secret',
                    'name':secret,
                    'namespace':module_args['release_namespace'],
                    'kubeconfig':module_args['kubeconfig'],
                    'context':module_args['context'],
                    'validate_certs': module_args['validate_certs']
                },
                task_vars=task_vars,
            )

        return True
    
    def install_helm(self,module_args,task_vars):
        module_args['state'] = 'present'
        return self._execute_module(
            module_name="kubernetes.core.helm",
            module_args=module_args,
            task_vars=task_vars,
        )
    
    def run(self, tmp=None, task_vars=None):
        """handler for k8s options"""
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        remote_transport = self._connection.transport != "local"

        new_module_args = copy.deepcopy(self._task.args)
        
        new_module_args=validate_helm_package(new_module_args)

        kubeconfig = self._task.args.get("kubeconfig", None)
        if kubeconfig:
            try:
                self.get_kubeconfig(kubeconfig, remote_transport, new_module_args)
            except AnsibleError as e:
                result["failed"] = True
                result["msg"] = to_text(e)
                result["exception"] = traceback.format_exc()
                return result
        

        # helm install 
        module_return = self.install_helm(
            module_args=new_module_args,
            task_vars=task_vars,
        )

        if module_return.get('status',{}).get('status',"") != "deployed":
            # try to install after deleting secret
            self.remove_helm_secret(
                module_args=new_module_args,
                task_vars=task_vars,
            )

            module_return = self.install_helm(
                module_args=new_module_args,
                task_vars=task_vars,
            )

        result.update(module_return)

        return self._ensure_invocation(result)