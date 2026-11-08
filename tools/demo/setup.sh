rm -rf /tmp/cd-demo && mkdir -p /tmp/cd-demo/src/app && cd /tmp/cd-demo
git init -q -b main && git config user.name demo && git config user.email demo@example.com
printf '[project]\nname = "app"\nversion = "1.0.0"\n' > pyproject.toml
echo 'def f(): return 1' > src/app/__init__.py
git add -A && git commit -qm "1.0.0" && git tag v1.0.0
echo 'def f(): return 2' > src/app/__init__.py
git commit -qam "fix f"
