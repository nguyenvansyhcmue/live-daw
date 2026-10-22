#pragma once
#include "NotePolicy.h"
#include <cmath>
#include <limits>
struct MusicalPolicy {
    static int nearestLegalNote (double desiredMidi, const NotePolicySnapshot& policy,
                                 int preferredNote) noexcept
    {
        auto bestNote = -1;
        auto bestDistance = std::numeric_limits<double>::infinity();
        for (int note = 0; note <= 127; ++note)
        {
            if (! policy.isLegalTarget (note))
                continue;

            const auto distance = std::abs (static_cast<double> (note) - desiredMidi);
            if (distance < bestDistance
                || (distance == bestDistance && note == preferredNote)
                || (distance == bestDistance && bestNote != preferredNote && note < bestNote))
            {
                bestNote = note;
                bestDistance = distance;
            }
        }
        return bestNote;
    }
    static int directedLegalNote (double desiredMidi, const NotePolicySnapshot& policy,
                                  bool upward) noexcept
    {
        const auto initial = upward ? static_cast<int> (std::floor (desiredMidi)) + 1
                                    : static_cast<int> (std::ceil (desiredMidi)) - 1;
        for (int note = initial; note >= 0 && note <= 127; note += upward ? 1 : -1)
            if (policy.isLegalTarget (note))
                return note;
        return -1;
    }
    static int adjacentLegalNote (int currentNote, const NotePolicySnapshot& policy,
                                  int direction) noexcept
    {
        for (int note = currentNote + direction; note >= 0 && note <= 127; note += direction)
            if (policy.isLegalTarget (note))
                return note;
        return -1;
    }
    static int selectPolicyTarget (double desiredMidi, NoteRule sourceRule,
                                   const NotePolicySnapshot& policy, int currentTarget) noexcept
    {
        // Directional policies deliberately do not fall back to a nearest
        // note on the other side. A missing target returns -1 (unity/dry).
        if (sourceRule == NoteRule::IllegalUp)
            return directedLegalNote (desiredMidi, policy, true);
        if (sourceRule == NoteRule::IllegalDown)
            return directedLegalNote (desiredMidi, policy, false);
        return nearestLegalNote (desiredMidi, policy, currentTarget);
    }
};
