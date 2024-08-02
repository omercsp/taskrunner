#!/bin/bash

for d in *; do
	[[ ! -d $d ]] && continue
	touch $d/stderr
done
