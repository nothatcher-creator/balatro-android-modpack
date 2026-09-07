#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>
#include "pitch_periodicity.h"

static std::vector<float> synth(int sr, double seconds, int midi,
                                float fundamental, float h2, float h3) {
    const double f = 440.0 * std::pow(2.0, (double(midi) - 69.0) / 12.0);
    std::vector<float> x(size_t(sr * seconds));
    for (size_t i = 0; i < x.size(); ++i) {
        const double t = double(i) / sr;
        const double env = std::min(1.0, t / 0.012) * std::exp(-0.25 * t);
        x[i] = float(env * (fundamental * std::sin(2*M_PI*f*t)
                          + h2 * std::sin(2*M_PI*2*f*t)
                          + h3 * std::sin(2*M_PI*3*f*t)));
    }
    return x;
}

static void require(bool ok, const char* msg) {
    if (!ok) { std::cerr << "FAIL: " << msg << "\n"; std::exit(1); }
}

int main() {
    constexpr int sr = 22050;
    auto f2 = synth(sr, 0.55, 41, 0.22f, 0.95f, 0.38f);
    const float trueF2 = basscribe::event_periodicity_score(f2, sr, 0.04, 0.38, 41);
    const float octave = basscribe::event_periodicity_score(f2, sr, 0.04, 0.38, 53);
    const float fifthish = basscribe::event_periodicity_score(f2, sr, 0.04, 0.38, 48);
    require(trueF2 > octave + 0.025f, "F2 must beat its strong octave harmonic");
    require(trueF2 > fifthish + 0.045f, "F2 must beat a false C3 candidate");
    require(basscribe::best_periodicity_midi(f2, sr, 0.04, 0.38, 35, 56) == 41,
            "global periodicity search must recover F2 from outside the +/-2 candidate window");

    auto c3 = synth(sr, 0.55, 48, 0.62f, 0.35f, 0.18f);
    const float trueC3 = basscribe::event_periodicity_score(c3, sr, 0.04, 0.38, 48);
    const float falseF2 = basscribe::event_periodicity_score(c3, sr, 0.04, 0.38, 41);
    require(trueC3 > falseF2 + 0.055f, "real C3 must not be pulled down to F2");
    require(basscribe::best_periodicity_midi(c3, sr, 0.04, 0.38, 35, 56) == 48,
            "global periodicity search must keep a genuine C3");

    std::cout << "pitch periodicity regression: PASS\n";
    return 0;
}
