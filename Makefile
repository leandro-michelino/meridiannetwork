TF_DIR := terraform
ANSIBLE_DIR := ansible
INVENTORY := $(ANSIBLE_DIR)/inventory/oci.ini

.PHONY: help tf-init tf-fmt tf-validate tf-plan tf-apply tf-destroy inventory ansible-requirements ping deploy

help:
	@echo "Meridian OCI Network Monitor"
	@echo ""
	@echo "Terraform:"
	@echo "  make tf-init       Initialize Terraform"
	@echo "  make tf-plan       Show OCI infrastructure plan"
	@echo "  make tf-apply      Create or update OCI infrastructure"
	@echo "  make tf-destroy    Destroy OCI infrastructure"
	@echo ""
	@echo "Ansible:"
	@echo "  make inventory     Render Ansible inventory from Terraform outputs"
	@echo "  make deploy        Configure the OCI host and publish the dashboard"

tf-init:
	terraform -chdir=$(TF_DIR) init

tf-fmt:
	terraform -chdir=$(TF_DIR) fmt -recursive

tf-validate:
	terraform -chdir=$(TF_DIR) validate

tf-plan: tf-fmt
	terraform -chdir=$(TF_DIR) plan

tf-apply: tf-fmt
	terraform -chdir=$(TF_DIR) apply

tf-destroy:
	terraform -chdir=$(TF_DIR) destroy

inventory:
	@mkdir -p $(dir $(INVENTORY))
	terraform -chdir=$(TF_DIR) output -json | python3 scripts/render_inventory.py > $(INVENTORY)
	@echo "Inventory written to $(INVENTORY)"

ansible-requirements:
	ansible-galaxy collection install -r $(ANSIBLE_DIR)/requirements.yml

ping: inventory
	ansible -i $(INVENTORY) meridian -m ping

deploy: inventory ansible-requirements
	ansible-playbook -i $(INVENTORY) $(ANSIBLE_DIR)/playbooks/bootstrap.yml
