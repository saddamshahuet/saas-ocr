# Cloud GPU/TPU Providers: Pricing, Instance Types, and Features (September 2025)

---

## 1. **Amazon Web Services (AWS)**
- **Instance Types:** Wide range (P4, P5, G4, G5, Inf1, Trn1, etc.), including NVIDIA A100, H100, V100, T4, and custom Inferentia/Trainium chips.
- **Pricing:** On-demand, spot, reserved, and savings plans. Example: p4d.24xlarge (8x A100 40GB) is ~$32.77/hr (on-demand, us-east-1). Spot discounts up to 90%.
- **SageMaker:** Managed ML platform, pay-per-use for training, inference, notebooks, and data processing. Free tier available.
- **Strengths:** Global reach, mature ecosystem, flexible billing, serverless options (SageMaker), and custom silicon.
- **Limitations:** Egress fees, complex pricing, GPU quotas, and limited multi-GPU scaling for some instance types.

---

## 2. **Google Cloud Platform (GCP)**
- **Instance Types:** A2 (A100), A3 (H100), G2 (L4), T4, V100, P100, P4, and Cloud TPU v2/v3/v4.
- **Pricing:** On-demand, committed use, and preemptible (spot) VMs. Example: A100 40GB ~$2.93/hr, H100 80GB ~$11.34/hr (us-central1).
- **Vertex AI:** Managed ML platform, pay-per-use for training, prediction, pipelines, and feature store. Serverless and custom scaling.
- **Strengths:** Sustained use discounts, spot/preemptible savings, TPUs for large-scale training, and integrated AI services.
- **Limitations:** GPU availability varies by region, quotas, and some instance types require minimum node counts.

---

## 3. **Microsoft Azure**
- **Instance Types:** NC, ND, NV, NDv2, ND A100 v4, NCas_T4_v3, and more. GPUs: K80, P40, V100, A100, T4, M60, H100, H200, and FPGAs.
- **Pricing:** On-demand, reserved, spot. Example: NC6 (K80) ~$657/mo, NCas_T4_v3 (T4) ~$384/mo, ND96asr A100 v4 (8x A100) ~$19,854/mo.
- **Azure ML:** Managed ML platform, pay-per-use for compute, storage, and managed endpoints.
- **Strengths:** Deep enterprise integration, hybrid/on-prem options, and broad GPU selection.
- **Limitations:** Some GPU SKUs are region-limited or being retired, and pricing can be complex.

---

## 4. **Lambda Labs**
- **Instance Types:** B200, H100, A100, A10, V100, RTX A6000, RTX 6000, GH200, and more. Multi-GPU up to 8x.
- **Pricing:** On-demand, pay-per-minute. Example: 8x H100 SXM $2.99/hr per GPU, 8x B200 $4.99/hr per GPU, 8x A100 SXM $1.79/hr per GPU.
- **Features:** ML-optimized images, Jupyter access, no egress fees, API for automation, and 1-click clusters up to 512 GPUs.
- **Strengths:** Fast access to latest NVIDIA GPUs, simple pricing, and ML-first experience.
- **Limitations:** Some instance types may require business validation for access.

---

## 5. **CoreWeave**
- **Instance Types:** GB300 NVL72, GB200 NVL72, B200, H100, H200, L40, L40S, A100, RTX PRO 6000 Blackwell, and more.
- **Pricing:** On-demand. Example: 8x B200 $68.80/hr, 8x H100 $49.24/hr, 8x A100 $21.60/hr, 8x L40 $10/hr.
- **Features:** No egress fees, free internal networking, managed Kubernetes, and up to 60% reserved discounts.
- **Strengths:** Access to latest NVIDIA hardware, high storage bandwidth, and large-scale clusters.
- **Limitations:** Some high-end SKUs require sales contact, and pricing can change with demand.

---

## 6. **RunPod**
- **Instance Types:** H200, B200, H100 (NVL, PCIe, SXM), A100 (PCIe, SXM), L40S, RTX 6000 Ada, A40, L40, RTX A6000, RTX 5090, 4090, 3090, A5000, L4.
- **Pricing:** Community and Secure Cloud. Example: H200 $3.59/hr, B200 $5.98/hr, H100 NVL $2.59/hr, A100 PCIe $1.19/hr, L40S $0.79/hr, RTX 3090 $0.22/hr.
- **Serverless:** Per-second billing, flex and always-on workers, e.g., H100 $0.00116/s ($4.18/hr).
- **Features:** No ingress/egress fees, persistent/ephemeral storage, and global regions.
- **Strengths:** Low prices, flexible serverless, and wide GPU selection.
- **Limitations:** Community cloud may have variable availability.

---

## 7. **Vast.ai**
- **Instance Types:** Marketplace for RTX 5090, H200, H100, 4090, 3090, A100, and more.
- **Pricing:** Marketplace-driven, e.g., RTX 5090 $0.36/hr, H200 $2.35/hr, H100 $1.65/hr, 4090 $0.34/hr, 3090 $0.22/hr.
- **Features:** No minimum contracts, pay-as-you-go, scale up to 64+ GPUs, and auction/interruptible pricing for extra savings.
- **Strengths:** Lowest prices, huge variety, and instant scaling.
- **Limitations:** Quality and support can vary by provider, and some offers may require manual vetting.

---

## 8. **Exoscale**
- **Instance Types:** GPU A30, GPU2 (V100), GPU3 (A40), GPU A5000, GPU 3080ti.
- **Pricing:** Example: GPU A30 Small (1x A30) €1.23/hr, GPU2 Small (1x V100) €1.38/hr, GPU3 Small (1x A40) €2.13/hr.
- **Features:** European data centers, business validation for GPU access, and pay-as-you-go.
- **Strengths:** Transparent pricing, European compliance, and multiple GPU generations.
- **Limitations:** GPU access requires business validation, and some SKUs are only in specific zones.

---

## 9. **Linode (Akamai Connected Cloud)**
- **Instance Types:** RTX 4000 Ada, Quadro RTX 6000, and others.
- **Pricing:** Example: $350/mo (16GB, 1x GPU), $446/mo (32GB, 1x GPU), $700/mo (32GB, 2x GPU), $892/mo (64GB, 2x GPU).
- **Features:** Flat-rate pricing, no egress fees, and simple plans.
- **Strengths:** Predictable pricing, good for small/medium workloads.
- **Limitations:** Limited GPU selection and not as competitive for high-end AI.

---

## 10. **Hetzner**
- **Instance Types:** Shared and dedicated vCPU, no direct GPU cloud (as of 2025).
- **Pricing:** Extremely low for CPU, e.g., €3.79/mo for 2 vCPU, 4GB RAM.
- **Features:** European data centers, GDPR compliance, and REST API.
- **Strengths:** Best for CPU workloads, unbeatable price-performance for general compute.
- **Limitations:** No direct GPU cloud, only CPU-focused.

---

## 11. **IBM Cloud**
- **Instance Types:** L40s, A100 PCIe, Intel Gaudi 3, and others (with promotions).
- **Pricing:** Custom, with frequent promotions (e.g., 50% off for new clients on L40s/A100).
- **Features:** Flexible contracts, hybrid/multicloud, and enterprise focus.
- **Strengths:** Enterprise support, compliance, and hybrid options.
- **Limitations:** Pricing is less transparent, and GPU access may require sales contact.

---

## 12. **Oracle Cloud Infrastructure (OCI)**
- **Instance Types:** AMD, Arm, and NVIDIA GPUs (A100, V100, etc.).
- **Pricing:** Consistent low pricing globally, e.g., 50% less than competitors for compute.
- **Features:** Free tier, $300 credits, and consistent services in all regions.
- **Strengths:** Low cost, global reach, and strong for Oracle workloads.
- **Limitations:** GPU selection and availability may be limited compared to hyperscalers.

---

## 13. **Paperspace (DigitalOcean)**
- **Instance Types:** A100, A40, A6000, 3090, 3080, and more.
- **Pricing:** Pay-per-use, e.g., A100 $2.30/hr, A40 $1.10/hr, 3090 $0.90/hr.
- **Features:** ML platform (Gradient), Jupyter, and team plans.
- **Strengths:** Simple pricing, ML-focused, and good for prototyping.
- **Limitations:** Some high-end GPUs may have limited availability.

---

### **Key Takeaways**
- **Best for lowest price:** Vast.ai, RunPod, Lambda Labs (for on-demand, spot, and auction pricing).
- **Best for enterprise/managed ML:** AWS, GCP, Azure, IBM Cloud.
- **Best for latest GPUs:** Lambda Labs, CoreWeave, RunPod, AWS, GCP.
- **Best for European compliance:** Exoscale, Hetzner.
- **Best for serverless AI:** RunPod, GCP Vertex AI, AWS SageMaker.

---

**Note:** All prices are subject to change, may vary by region, and do not include storage, networking, or additional service fees. Always use the provider’s calculator for exact quotes.

If you need a detailed comparison table or a recommendation for a specific use case (e.g., LLM training, inference, or cost optimization), let me know!
