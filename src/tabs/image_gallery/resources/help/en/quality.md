## Quality Metrics

Every image gets a score from 0 to 100; higher is better. A score summarizes several measurements of the image, such as sharpness, exposure, noise, and color.

### Score measurement {#measured-metrics}

The score is computed automatically; details live in Quick Look.

### Score locations {#where-scores}

- **Quick Look** — per-image metric rows with the raw readings.
- **Card dots** — dots on the card flag remarks.
- **{{tr:image_gallery.sort_quality}}** — AI quality first; unscored items sink to the end.

### Reference comparison {#modes}

Comparison against a reference, assigned manually.

### Reference assignment {#reference-source}

**Source** is the image chosen as the reference to compare against.

{{tr:image_gallery.action.set_as_source}} assigns the reference to compare against. Scores update after assignment.
