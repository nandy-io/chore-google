docker_build('daemon-chore-google-nandy-io', './daemon')

k8s_yaml(kustomize('.'))

k8s_resource('daemon', port_forwards=['26749:5678'])