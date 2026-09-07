# MGC Languages v6.0.13

## Legacy Frontend Cleanup

- Reduced `legacy-app` bridge to the compatibility surface still required by session/language lifecycle plus learning/practice renderers.
- Removed Manager and Admin renderer exports from the bridge.
- Added `legacy-retirement` runtime boundary for 24 superseded `app.js` globals.
- Retirement only activates after all replacement owner modules are present.
- Active learning (`home/topics/quiz/course30`) and practice (`roleplay/games/xp`) legacy renderers remain intentionally available for the next migration stages.
- Added v6.0.13 regression shard, static preflight and dedicated CI gate.
- Backend API, database migrations, language content, XP rules and runtime APP_VERSION are unchanged.
