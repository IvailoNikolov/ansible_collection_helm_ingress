# Ansible Collection - ivailo.helm_wrapper

Documentation for the collection.

### Modules


Name | Description
--- | ---
ivailo.helm_wrapper.install|Install Helm Chart with Fail Safe retry and version check

## Installation and Usage

### Installing the Collection from Ansible Galaxy

create a file name "requirements.yml"
```yaml
---
collections:
    - name: kubernetes.core
      version: 2.3.2
    - name: git+https://github.com/IvailoNikolov/ansible_collection_helm.git master
```

Before using the Kubernetes collection, you need to install it with the Ansible Galaxy CLI:

    ansible-galaxy install -r ./requirements.yml

### Role example

It allows to install the chart on a kubernetes cluster.
Please follows the offical [kubernetes.core.helm module](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html) to update parameters

You need to use a /.kube/config file to access the kubernetes cluster.

```yaml
---
- name: "Deploy Name of your chart chart"
  ivailo.helm_wrapper.install:
    name: Release name to manage.
    chart_repo_url: Chart repository URL where to locate the requested chart.
    chart_version: Chart version to install. If this is not specified or invalides, the latest version is installed.
    chart_ref: chart_reference on chart repository.
    release_namespace: Release name to manage.
    create_namespace: Create the release namespace if not present.
    values: Value to pass to chart. example "{{ helm_cert_manager_values | to_json }}"
    values_files: Value files to pass to chart.
    wait: When release_state is set to present, wait until all Pods, PVCs, Services, and minimum number of Pods of a Deployment are in a ready state before marking the release as successful.
    force: Helm option to force reinstall, ignore on new install.
    atomic: If set, the installation process deletes the installation on failure.
    skip_crds: Skip custom resource definitions when installing or upgrading.
    update_repo_cache: Run helm repo update before the operation
    binary_path: The path of a helm binary to use.
    context: Helm option to specify which kubeconfig context to use.
    kubeconfig: Helm option to specify kubeconfig path to use.
    validate_certs: Whether or not to verify the API server’s SSL certificates
```


### Playbook example

Inventory example:


```yaml
---

- hosts: master[0]
  serial: 1
  become: yes
  roles:
   - role: ivailo.helm_wrapper.helm_prereq
```