# Lanes

The throughput scenarios open several pull requests at once. Each one edits its
own file in this directory (`lane-1.txt`, `lane-2.txt`, ...), so they never
conflict textually. That isolates the variable being measured: how long it takes
to land N independent, green pull requests under each protection model.
