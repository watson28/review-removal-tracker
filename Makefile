ANSIBLE_DIR := ansible
INVENTORY := $(ANSIBLE_DIR)/inventory.yml
PLAYBOOK := $(ANSIBLE_DIR)/playbook.yml
VAULT_FILE := $(ANSIBLE_DIR)/group_vars/all/secrets.yml

.PHONY: deploy deploy-check vault-edit

deploy:
	cd $(ANSIBLE_DIR) && ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass

deploy-check:
	cd $(ANSIBLE_DIR) && ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass --check --diff

vault-edit:
	ansible-vault edit $(VAULT_FILE)
