sudo swapoff -a
sudo kubeadm reset
sudo kubeadm join 143.248.55.76:6443 --token w02dac.45vva0vjb0jta4v9 --discovery-token-ca-cert-hash sha256:395efa95b5d512a3aa07d404125a14e80bea28a8d9adfda56a03680c64c77632