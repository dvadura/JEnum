Project Names:
==============
Project names can be almost anything but cannot contain any character from this
set [/-,;?*#$<>%!.\'"^~`].

Version Sets:
=============
A version set is a bundle containing packages that were required, built and deployed and
bundled together into an artifact bundle. The VersionSet identifies the versions of all packages that were
needed to produce the bundle. The Key idea is that, given a VersionSet, you should be able to 100%
reproduce a build including released snapshots of any dependent packages that the build required.

Every package in the version set comes from a git repository. There may be special git repositories that represent
globally latest versions of packages as well as development repos built with source package versions to bundle into
the version set. For example, a git repository may include a project called live, which includes versioned
artifacts that are always deployed to a deployment target node.

An artifact can contain the dependency: vs-Live-bif@tip. This means that the project depends on the
Live Artifact which publishes the latest known good versions of commonly used packages. This allows security fixes
to be pushed to all dependent projects by updating Live on all running systems and restarting installed services.
By treating live as a dependent version set from a git repository, It is possible to reproduce a build by pulling
a specific Tag from the repositories of all version sets. The tag identifies a unique build and allows a build to
be fully reproduced.

That is the goal! Full reproduction of prior builds with 100% fidelity. Otherwise, it may be very difficult to
track down a bug that occurs as the result of a dependent package update.

By Example:
===========
Consider the following Git global MONO repository contents organized by Organization/{repositories...}

     Organization   Repositories
     Live           repo1, repo2
     PrjA           repoAA, repoAB
     PrjB           repoB
     bif            new-project

The Live namespace is special, that is where 3rd-Party packages live that are deployed to all deployment targets.
Every package in Live is guaranteed to be current and up to date on deployment target hosts and containers.

new-project depends on repo1 from live@tip, repoAA from PrjA@R1.2#tip and repoB from PrjB at its tip at
build event 30020303394 (ie. the 30020303394 revision). In this case file tree under new-project/Config/vs would
look like:

- need current vs pin
- need repo per org/namespace
- need given namespace@eventid the vs config at that point.
   . can be done via include iff the __include__ directive is in the top level vs.js5 file.
     and must be updated when pin is modified.
- need ids, and files of all events relative to the vs.
- required single read of top level file with interpolation to get the rest.

new-project/Config/vs
                    // having this allows current VS to have deps from namespaces in other repositories
   repos.js5:       {repos: {
                        master: {url: 'http://localhost/index.html', user: '', spaces: ['bif',...]},
                        ...
                    }
   namespace.js5:   { namespace: 'bif' }     // tells us which namespace this project is in
   pin.js5:         { pin: 'tip' }           // this tells us which vs is the current VS

   index/
      // each index file covers a period of 50*24*3600(s), (4320000s) since the epoch, ie. each index file includes
      // a block of events that fall into a 4320000s block of time since the epoch.
      // If a new entry based on UTC time falls outside the current index file (ie. if included in the file then
      // the file would cover a period > 43200000s, then the current index file is renamed to the time block id
      // of the prior file, and a new latest.js5 file is created.
      //
      // timeblock id's are time in seconds since epoch divided by 4320000.
      latest.js5:
         {
            block: <timeblockid>,
            <mtime>: {mtime: <mtime>, build: <buildid>, version: <versionid>, tag: <tagid>, userid: <userid>},...
         }

   <namespace>/
      tip.js5
      {
           ctime:   <datetime>            // UTC
           mtime:   <timestamp>           // UTC
           package: <packageid>
           version: <versionid>
           build:   <buildid>
           tag:     vs-<package>-<org>@tip,<eventid>  // tag that matches latest commit, no tag, no commit yet

           needs: [
              'vs-repo1-Live@tip',               // always the latest
              'vs-repoAA-PrjA@R1.2#tip',         // pinned to the tip of a specific release
              'vs-repoB-PrjB@tip,30020303394',   // pinned to a specific build event
           ]
      }

      events/.../<timestamp>.js5
          {
          }

Version Set Naming:
===================
Every version set has a name that comprises the package name followed by the organization to which the version set
belongs followed by either the event reference. The organization names create namespaces; in the example above,
there are 4 namespaces Live, PrjA, PrjB, and bif (the default).

The event reference is formed from:

    <[release#]tip>[,<eventid>]

where both the <release> and <eventid> portions are optional.

Repository Tags:
================
When an event takes place all dependent components of the project issuing the event are tagged. The tags take the
form:

   vs-<package>-<namespace>@<event-ref>,<buildid>

This means that we can search tags in repositories and yield all builds with the same id (could happen), and
pull their project specific event refs.

Branches:
=========
All projects are managed on the master branch. Each developper executes pull-rebase's to update their local state
via bif pull. bif commit then creates pull-requests by branching master and creating a <developer>-<buildid>-<eventid>
branch which when accepted/approved will be rebased and merged into master.

Commits of Version Set Config:
==============================
Config/vs is updated when one of the following events takes place:

    1) a new release build is made in this case the tip.js5 is copied to a hash of tip.js5.
    2) a merge to add a new dependent package or remove an old one is made, in this case tip.js5 is updated.
    3) a merge from live is made and some of the dependencies are updated, in this case tip.js5 is updated.
    4) a pull-request is generated
    5) a pull-request is approved and merged into master.

These commits are then in line with the project change history and are recorded in the git history log.
This provides a single source of truth about what the state of the project package, it's dependencies, and
how we got here is.

Repository Hash:
================
Git computes a hash of every repository commit. These are managed by git and are not used by bif.

Mutations:
==========
During an update event all package revisions making up a version set are transitively updated and are pulled
(if needed) from the global repository.

Thus, in theory, a version set includes the needed tooling that performs the builds, tests them, packages, and deploys
them; as well as the source and dependent libraries of the package being built.

So the combination of:
   - tooling
   - source packages
   - dependent libraries
   - runtime sidecar deployments (think required local co-deployed services)

when named as a versionSet identifies the list of items and their versions that need to be bundled together
so that a consistent deployment, test or build can take place.

Visually (THIS IS OUT OF DATE):
===============================
- review clearlinux.org mixer, and clearlinux.org swupd for updating software, might be able to use them instead
  of rolling our own.

  TRIGGER EVENT ====>   DEPENDENT TOOLS  ===>   BUILD/CACHE
                        DEPENDENT LIBS   ===>   BUILD/CACHE

                        BUILD SRC PKG    ===>   UTEST ===> APPROVE

                        DEPENDENT LIBS
                        LIVE REPO        ===>   BUILDER  ===> VS-BUNDLER ===> VS@EVENTID ===> TEST ===> RELEASE ==> DEPLOY & STAGE
                        PLATFORM REPO                                              (smoke,fire,inferno,volume)
