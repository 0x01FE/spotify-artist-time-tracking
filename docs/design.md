# Design

This document is meant to explain how the application checks and records if a user is listening to a song on Spotify.

There are two major systems when it comes to listening, a check, and juggling between the multiple users the system needs to watch.

## Listening Check

Starting with the listening check there is a process that the program goes through to decide if a user is "listening" to a song and if the program deems the user has listened to it for long enough then it is recorded as a "listen event" in the SQLite database.

### Wait Times

The program decides how long to wait by using a few variables from the config + some math related to the users progress into a track.
How the wait time is decided will be marked in each case in `The Process`.

### The Process

The process for deciding if a user is listening to a song goes as follows,

#### Case Double Check Pass
The program is double checking the users progress in a song, the song is the __SAME__ as last time, and the progress threshold is met
    Result: Record a listen event for this user and song
    Wait Time: ACTIVE_WAIT_TIME

#### Case Double Check Fail 1
The program is double checking the users progress in a song, the song is the __SAME__ as last time, BUT the progress still does __NOT__ meet the threshold.
    Result: Wait and double check again
    Wait Time: track duartion * PROGRESS_THRESHOLD - current progress

#### Case Double Check Fail 2
The program is double checking the users progress in a song, the song is __NOT__ the same as last time.
    Result: The program adds the last track and marks it as skipped. The time spent listening to the last song is calculated by the last progress recorded for the last song + the wait time - current progress
    Wait Time: ACTIVE_WAIT_TIME

#### Case No Double Check
User probably just started listening to music and the track progress threshhold has not been met.
    Result: Mark double check as true and wait
    Wait Time: track duartion * PROGRESS_THRESHOLD - current progress

#### Other cases
User is not listening to a track
    Result: Double check is marked as false

Wait Time is over MAX_ACTIVE_WAIT_TIME
    Result: Wait Time is set to MAX_ACTIVE_WAIT_TIME
    Why?: In case a song is 30 minutes long and the program wants to wait like 26 minutes to check if the user is done. If the user skipped to another song 2 minutes the program could miss a lot of listening history.


## Multiple Users








