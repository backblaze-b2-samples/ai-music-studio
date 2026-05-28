<!-- last_verified: 2026-05-27 -->
# App Workflows

User journeys inside the application.

## The studio journey

- User navigates to `/projects` and clicks **New project**
- Names the project ("Lo-fi study session"), optionally describes it
- Clicks into the project — lands on `/projects/<id>`
- Writes a prompt ("warm ambient pad with soft bells, slow tempo"),
  adds optional style / avoid tags, and toggles instrumental mode if wanted
- Clicks **Generate** — the button shows a generating state while the
  provider call returns the new `Track` payload
- The track appears as a node in the **Revision Tree** below the form;
  TanStack Query has already invalidated the tree query so it re-renders
  with the new node
- Clicks **Play** on the node — the player swaps in for the action row,
  fed by a short-lived presigned URL
- Clicks **Branch** on the node — the form re-titles to "Branch from
  selected track" and shows New Take / Extend / Restyle controls; the
  next generate call lands as a child node in the tree
- Picks two nodes (**A** then **B**) — the **Compare** dialog opens
  with both tracks side-by-side, dual `<audio controls>`, and a diff
  list (prompt / controls / branch mode / duration / audio-metadata)
- Switches to the **Project Files** tab to see the project's scoped B2
  view: `project.json`, every `tracks/<id>/audio.<ext>` + `track.json`
- Done. Closes the project — every artifact is still in B2 under
  `projects/<id>/`; reopening the project re-builds the tree fresh from
  the sidecars (no client cache assumed)
- See: [Projects](features/projects.md), [Generation](features/generation.md), [Revision History](features/revision-history.md), [Project Asset Explorer](features/project-asset-explorer.md)

## Browse the cross-project Track Library

- User navigates to `/library`
- Page loads the asset list from `GET /library` (sorted newest-first) —
  this is every legacy `audio/` object plus generated project-scoped
  tracks
- Each `AudioAssetCard` shows: filename, duration · sample rate ·
  channels · created date, an inline waveform stub, and Play / Download
  / Delete actions
- **Play / Download / Delete / Bulk delete** behave as in the underlying
  starter
- Empty bucket shows "Nothing here yet — generate a track from a project
  to see it appear in the cross-project library"
- See: [Track Library](features/track-library.md), [Audio Metadata Extraction](features/audio-metadata.md)

## Browse the Full Bucket (Files)

- User navigates to `/files`
- Page loads file list from `GET /files` (sorted most recent first)
- Files displayed in tree view with folders and type-specific icons
- Top-level folders auto-expand on load — so `projects/`, `audio/`, and
  `uploads/` are immediately visible
- Hover a file row to see action buttons (preview / download / delete)
- **Preview**: opens dialog with image/PDF preview + metadata panel for non-audio content
- **Download**: fetches presigned URL, browser downloads file
- **Delete**: removes file from B2, row removed from tree, toast confirms
- **Bulk delete**: per-row and per-folder checkboxes
- Empty bucket shows "This bucket is empty"
- See: [Bucket Explorer](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Header offers two actions: **Open projects** and **Browse library**
- Empty state: when the bucket holds no tracks, the page collapses to a
  single hero card ("No tracks yet — create your first project") with
  the projects CTA. The grid below is hidden until the first track lands
- With tracks present, the dashboard loads in parallel: stats, recent
  tracks, generation activity
- **Stats tiles**: Tracks, Total Duration, Generated Today, Audio
  Storage
- **Generation activity chart**: last 7 days as a bar chart
- **Recent Tracks table**: last 10 tracks with Filename / Duration /
  Format / Date / Play (inline `<audio>` in a small dialog)
- See: [Dashboard](features/dashboard.md)
