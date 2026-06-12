# Hermes Vault Plugin 
 
<img width="1864" height="673" alt="{01378AE8-761F-4815-98B5-0F17FEE8B2DD}" src="https://github.com/user-attachments/assets/493df334-3e84-422b-a423-751f5c70deed" />
 
## Install

```bash
hermes plugin uninstall vault   # if already installed
cd ~/.hermes/plugins
tar xzf /path/to/hermes-vault-fixed.tar.gz
mv hermes-vault-archive vault
hermes plugins enable vault
python3 ~/.hermes/plugins/vault/vault_init.py
hermes dashboard --force-discover
```
