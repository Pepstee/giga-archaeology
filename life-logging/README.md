# Life Logging

`life-logging/` is the project boundary for private evidence captured from daily life.
Each modality is an independent subproject with its own ingestion, processing, review,
retention and promotion rules.

Current subprojects:

- `audio-processing/` — wearable-recorder ingestion, transcription, diarisation,
  translation, review and approved-event export.

Raw observations never enter GIGA memory merely because they were captured. Processing
produces evidence packages; explicit review produces approved events; a separate GIGA
adapter controls permanent promotion.
