# 3.1.0

"ART!"

Previously cover art urls and artist icon urls were not being saved and causing extra Spotify API calls in some of my other applications. When new entries for albums or artists are added to the database these urls are saved with them.

## Changes
- Moved (most) SQL queries to files instead of being hard-coded
- Program now saves image urls with albums and artists

# 3.0.0

"Async Listen Rewrite"

Before this update the program handled having to keep track of multiple users with multiple processes. This turned out to be error prone and difficult to debug. The solution implemented in this update was rewriting the code to cycle between users listening to them asynchronously.

## Changes
- Async listening rewrite
- Started adding documentation to the repository.

