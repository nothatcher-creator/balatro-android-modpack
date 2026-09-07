#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace basscribe {

inline float midi_frequency(int midi) {
    return 440.0f * std::pow(2.0f, (float(midi) - 69.0f) / 12.0f);
}

inline float normalized_autocorrelation(const std::vector<float>& audio,
                                        int sample_rate,
                                        double center_seconds,
                                        int lag,
                                        int window = 1536) {
    if (audio.empty() || sample_rate <= 0 || lag < 2) return -1.0f;
    const int64_t center = int64_t(std::llround(center_seconds * double(sample_rate)));
    int64_t start = center - window / 2;
    if (start < 0) start = 0;
    if (start + window + lag >= int64_t(audio.size())) {
        start = int64_t(audio.size()) - window - lag - 1;
    }
    if (start < 0 || start + window + lag >= int64_t(audio.size())) return -1.0f;

    double mean_a = 0.0, mean_b = 0.0;
    for (int i = 0; i < window; ++i) {
        mean_a += audio[size_t(start + i)];
        mean_b += audio[size_t(start + i + lag)];
    }
    mean_a /= window;
    mean_b /= window;

    double ab = 0.0, aa = 0.0, bb = 0.0;
    for (int i = 0; i < window; ++i) {
        const double u = double(audio[size_t(start + i)]) - mean_a;
        const double v = double(audio[size_t(start + i + lag)]) - mean_b;
        ab += u * v;
        aa += u * u;
        bb += v * v;
    }
    const double denom = std::sqrt(std::max(1e-18, aa * bb));
    if (denom <= 1e-9) return -1.0f;
    return float(std::clamp(ab / denom, -1.0, 1.0));
}

inline float periodicity_at(const std::vector<float>& audio,
                            int sample_rate,
                            double center_seconds,
                            int midi) {
    const float f = midi_frequency(midi);
    if (f < 30.0f || f > float(sample_rate) * 0.45f) return -1.0f;
    const int lag = std::max(2, int(std::lround(float(sample_rate) / f)));
    const float c1 = normalized_autocorrelation(audio, sample_rate, center_seconds, lag);
    if (c1 < -0.99f) return c1;

    // A genuine fundamental stays periodic at two periods as well.  This tiny
    // consistency term helps reject bright overtone hypotheses without simply
    // forcing every candidate down an octave.
    float c2 = c1;
    if (lag * 2 < 900) {
        const float t = normalized_autocorrelation(audio, sample_rate, center_seconds, lag * 2);
        if (t > -0.99f) c2 = t;
    }
    return 0.92f * c1 + 0.08f * c2;
}

inline float event_periodicity_score(const std::vector<float>& audio,
                                     int sample_rate,
                                     double event_time,
                                     double event_duration,
                                     int midi) {
    if (audio.empty()) return -1.0f;
    const double dur = std::max(0.08, event_duration);
    const double t1 = event_time + std::min(0.050, std::max(0.020, dur * 0.20));
    const double t2 = event_time + std::min(dur * 0.50, std::max(0.055, dur * 0.42));
    const double t3 = event_time + std::min(dur * 0.76, std::max(0.085, dur * 0.66));
    const float a = periodicity_at(audio, sample_rate, t1, midi);
    const float b = periodicity_at(audio, sample_rate, t2, midi);
    const float c = periodicity_at(audio, sample_rate, t3, midi);
    std::vector<float> vals;
    if (a > -0.99f) vals.push_back(a);
    if (b > -0.99f) vals.push_back(b);
    if (c > -0.99f) vals.push_back(c);
    if (vals.empty()) return -1.0f;
    std::sort(vals.begin(), vals.end());
    if (vals.size() == 1) return vals[0];
    if (vals.size() == 2) return 0.5f * (vals[0] + vals[1]);
    // Median is robust to one transition/attack frame at the edge of a note.
    return vals[1];
}

inline int best_periodicity_midi(const std::vector<float>& audio,
                                int sample_rate,
                                double event_time,
                                double event_duration,
                                int min_midi,
                                int max_midi) {
    min_midi = std::max(0, min_midi);
    max_midi = std::min(127, max_midi);
    std::vector<std::pair<int,float>> scores;
    float best_score = -2.0f;
    for (int midi = min_midi; midi <= max_midi; ++midi) {
        const float s = event_periodicity_score(audio, sample_rate, event_time, event_duration, midi);
        scores.push_back({midi,s});
        if (s > best_score) best_score = s;
    }
    // Autocorrelation is naturally also high at integer multiples of the true
    // period.  If an octave-down candidate ties the shorter true period, pick
    // the higher MIDI among near-equal maxima rather than inventing a subharmonic.
    int best = min_midi;
    for (auto [midi, s] : scores) {
        if (s >= best_score - 0.020f && midi > best) best = midi;
    }
    return best;
}

} // namespace basscribe
