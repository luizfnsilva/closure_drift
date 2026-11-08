# Regenerate docs/demo-tag.gif from the repository root: vhs tools/demo/demo.tape
Output docs/demo-tag.gif
Set Shell "bash"
Set FontSize 13
Set Width 1300
Set Height 460
Set Theme "GitHub Dark"
Set TypingSpeed 40ms
Hide
Type `R=$PWD && source tools/demo/setup.sh && alias closure-drift="python3 $R/closure_drift.py" && export PS1='$ ' && clear`
Enter
Show
Type "# a fix is committed; tag the release"
Enter
Type "git tag v1.1.0"
Enter
Sleep 400ms
Type "closure-drift . --tag v1.1.0 | grep -E '^(tag|declare|TAG|A build|Next)'"
Enter
Sleep 4s
Type "# leave v1.1.0 alone; bump, commit, tag a new name"
Enter
Type "sed -i '' 's/1.0.0/1.1.1/' pyproject.toml && git commit -qam 1.1.1 && git tag v1.1.1"
Enter
Sleep 400ms
Type "closure-drift . --tag v1.1.1 | grep -E '^(tag|declared|TAG)'"
Enter
Sleep 4s
