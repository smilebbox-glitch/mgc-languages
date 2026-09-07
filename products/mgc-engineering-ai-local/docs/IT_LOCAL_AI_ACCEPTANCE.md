# IT acceptance checklist — local neural network

A build can be called "fully local" only if every item below passes.

- [ ] The generative model weights exist on a company-controlled disk.
- [ ] Embedding weights exist on a company-controlled disk.
- [ ] Reranker weights exist on a company-controlled disk.
- [ ] `/api/v1/local-ai/health` reports `air_gapped_mode=true` and `ready=true`.
- [ ] LLM/VLM base URLs resolve only to an internal container/host.
- [ ] The model-server port is not published to the corporate LAN or internet.
- [ ] Runtime containers have `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
- [ ] Docker uses preloaded images or an internal registry; `pull_policy: never` is active on the isolated deployment.
- [ ] Public internet egress is denied at firewall/VLAN level.
- [ ] The Engineering AI UI remains usable with the WAN route disabled.
- [ ] A test RAG question returns an answer and evidence while internet is disabled.
- [ ] A drawing/image test is processed by the internal multimodal model while internet is disabled.
- [ ] Model and image checksums are archived with the deployment record.

## Recommended demonstration to IT

1. Start the stack on the isolated host.
2. Show `docker compose -f docker-compose.airgap.yml ps`.
3. Show `/api/v1/local-ai/health`.
4. Disconnect/deny internet on the host or VLAN.
5. Run `./scripts/airgap_acceptance.sh`.
6. Upload a local PDF/STEP and ask a question.
7. Confirm the answer is generated and cites local evidence.

If step 6-7 succeeds with public internet denied, the generative inference path is demonstrably local.
