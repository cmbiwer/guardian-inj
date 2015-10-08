# guardian-inj

This is a repository for developing a Guardian node manager to perform hardware injections in LIGO.

Documentation is not accessible by the public at the moment. For more information on Guardian see: https://dcc.ligo.org/LIGO-T1500292

## how to run

First clone the repository and change directory into the top level of the cloned repository.

Then change the following environment variable that will tell ``guardian`` where to find the hardware injection module:
```
export GUARD_MODULE_PATH=${PWD}/lib
```

Now you can run it with:
```
guardian INJ
```
