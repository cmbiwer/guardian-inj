# guardian-inj

**This project has been moved to the non-public CDS user apps SVN for implementation.**

This is a repository for developing a Guardian node manager to perform hardware injections in LIGO.

Documentation is not accessible by the public at the moment. For more information on Guardian see: https://dcc.ligo.org/LIGO-T1500292

And here is a link to the suspensions guardian node manager as an example of an already implemented project: https://redoubt.ligo-wa.caltech.edu/svn/cds_user_apps/trunk/sus/common/guardian

## dependencies

The instructions assume you are running on a work station in the control room of the observatory.

You will need v1.19 of the GraceDB python API. You can get the package here: http://software.ligo.org/lscsoft/source/ligo-gracedb-1.19.tar.gz

Note that when you install the GraceDB python API it looks like there is no ``ligo/__init__.py`` file so you will have to create a blank file in order to import properly.

You will also v1.49.1 of the glue python package. You can get the package here: http://software.ligo.org/lscsoft/source/glue-1.49.1.tar.gz

## how to run

First clone the repository and change directory into the top level of the cloned repository.

Then change the following environment variable that will tell ``guardian`` where to find the hardware injection module:
```
export GUARD_MODULE_PATH=${PWD}/guardian
export PYTHONPATH=${PWD}/guardian:${PYTHONPATH}
```

Now you can run it with:
```
guardian INJ
```
