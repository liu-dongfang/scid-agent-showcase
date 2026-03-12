# SCID Showcase Transcript - Public Demo Case 01

**Date:** 2026-03-12

**Assistant:** **What has been most disruptive for you over the last few weeks?**

**Participant:** Work stress has been building up, my sleep has gotten lighter, and I have stopped enjoying things after work.

**Assistant:** **Have there been stretches where low mood stayed with you for most days?**

**Participant:** Yes, especially over the last month.

**Assistant:** **Have you also had episodes of high tension, fear, or panic that disrupted your routine?**

**Participant:** Yes, I had a few intense spikes where I had to step away from meetings.

```json
{
  "Overview": {
    "opening_context": {
      "presenting_problem": "Work stress, lighter sleep, lower enjoyment after work.",
      "onset_and_context": "Escalated over the last month during a heavy deadline period."
    }
  },
  "Screening": {
    "SCR_low_mood": {
      "binary_response": "YES"
    },
    "SCR_high_arousal": {
      "binary_response": "YES"
    }
  },
  "CORE_MODULE_MOOD": {
    "MOOD_sleep_disruption": {
      "presence": true,
      "duration_weeks": 4,
      "frequency": "almost_daily",
      "impairment_domains": [
        "work"
      ],
      "source_snippet": "My sleep has gotten lighter and I feel slower the next day."
    }
  },
  "CORE_MODULE_ANXIETY": {
    "ANX_worry_cycle": {
      "presence": true,
      "duration_weeks": 4,
      "frequency": "almost_daily",
      "impairment_domains": [
        "work",
        "social"
      ],
      "source_snippet": "I keep rehearsing everything that could go wrong."
    },
    "ANX_panic_like_episode": {
      "unexpected_onset": true,
      "peak_in_minutes": true,
      "symptom_count": 4,
      "avoidance_behavior": false,
      "impairment_domains": [
        "work"
      ],
      "source_snippet": "I had to leave the meeting room when it peaked."
    }
  }
}
```
