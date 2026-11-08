#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="vllm-project"
VLLM_IMAGE="vllm-cpu:0.27.0"
BENCHMARK_IMAGE="benchmark-api:0.1.0"
NODE="desktop-control-plane"

echo "==> Checking prerequisites..."

for cmd in docker kubectl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: $cmd is not installed"
        exit 1
    fi
done

echo "==> Building vLLM image..."
docker buildx build --builder default \
    -f docker/dockerfile \
    -t "$VLLM_IMAGE" \
    --load .

echo "==> Building Benchmark API image..."
docker buildx build --builder default \
    -f benchmark/Dockerfile \
    -t "$BENCHMARK_IMAGE" \
    --load .

echo "==> Importing images into Kubernetes node..."

docker save "$VLLM_IMAGE" -o /tmp/vllm-cpu.tar
docker cp /tmp/vllm-cpu.tar "$NODE:/root/vllm-cpu.tar"
docker exec "$NODE" ctr -n k8s.io images import /root/vllm-cpu.tar
rm -f /tmp/vllm-cpu.tar

docker save "$BENCHMARK_IMAGE" -o /tmp/benchmark-api.tar
docker cp /tmp/benchmark-api.tar "$NODE:/root/benchmark-api.tar"
docker exec "$NODE" ctr -n k8s.io images import /root/benchmark-api.tar
rm -f /tmp/benchmark-api.tar

echo "==> Creating namespace..."
kubectl apply -f kube/namespace.yaml

echo "==> Checking Kubernetes Secret..."
if ! kubectl get secret vllm-secret -n "$NAMESPACE" >/dev/null 2>&1; then
    echo "Kubernetes Secret does not exist."
    read -rsp "Enter Hugging Face token: " HF_TOKEN
    echo
    VLLM_API_KEY=$(openssl rand -hex 32)

    kubectl create secret generic vllm-secret \
        --namespace "$NAMESPACE" \
        --from-literal=HF_TOKEN="$HF_TOKEN" \
        --from-literal=VLLM_API_KEY="$VLLM_API_KEY"

    unset HF_TOKEN VLLM_API_KEY
else
    echo "Kubernetes Secret already exists. Keeping it."
fi

echo "==> Applying Kubernetes manifests..."

kubectl apply -f kube/configmap.yaml
kubectl apply -f kube/benchmark-configmap.yaml
kubectl apply -f kube/vllm-logging-config.yaml
kubectl apply -f kube/pvc.yaml
kubectl apply -f kube/vllm-service.yaml
kubectl apply -f kube/benchmark-service.yaml
kubectl apply -f kube/vllm-deployment.yaml
kubectl apply -f kube/benchmark-deployment.yaml

echo "==> Waiting for deployments..."

kubectl rollout status deployment/vllm \
    -n "$NAMESPACE" \
    --timeout=15m

kubectl rollout status deployment/benchmark-api \
    -n "$NAMESPACE" \
    --timeout=5m

echo
echo "==> Deployment completed!"
kubectl get pods -n "$NAMESPACE"
kubectl get services -n "$NAMESPACE"