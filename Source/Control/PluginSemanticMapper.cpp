#include "PluginSemanticMapper.h"

#include <algorithm>

namespace
{
juce::String normalise(juce::String value)
{
    return value.toLowerCase().retainCharacters("abcdefghijklmnopqrstuvwxyz0123456789");
}

bool hasAny(const juce::String& value, std::initializer_list<const char*> tokens)
{
    return std::any_of(tokens.begin(), tokens.end(), [&value] (const char* token)
    {
        return value.contains(token);
    });
}

bool isReverb(const juce::String& plugin)
{
    return hasAny(plugin, { "reverb", "room", "hall", "plate", "chamber", "verb" });
}

bool isDelay(const juce::String& plugin)
{
    return hasAny(plugin, { "delay", "echo", "tape", "repeat" });
}

bool isDynamics(const juce::String& plugin)
{
    return hasAny(plugin, { "compress", "limiter", "gate", "dynamics" });
}

PluginCategory categoryFor(const juce::String& plugin)
{
    if (hasAny(plugin, { "autotune", "vibeautotune", "wavestune", "pitchcorrect", "pitchcorrection" }))
        return PluginCategory::pitchCorrection;
    if (hasAny(plugin, { "proq", "equalizer", "equaliser", "parametriceq", "dynamiceq" }))
        return PluginCategory::equalizer;
    if (hasAny(plugin, { "deesser", "deess", "sibilance" })) return PluginCategory::deEsser;
    if (isReverb(plugin)) return PluginCategory::reverb;
    if (isDelay(plugin)) return PluginCategory::delay;
    if (isDynamics(plugin)) return PluginCategory::dynamics;
    if (hasAny(plugin, { "saturat", "distort", "exciter", "overdrive", "tape", "tube", "console" }))
        return PluginCategory::saturation;
    if (hasAny(plugin, { "chorus", "flanger", "phaser", "modulat", "rotary" }))
        return PluginCategory::modulation;
    if (hasAny(plugin, { "stereo", "imager", "width", "spreader" })) return PluginCategory::imaging;
    if (hasAny(plugin, { "utility", "gain", "trim", "balance" })) return PluginCategory::utility;
    return PluginCategory::unknown;
}

bool parameterHas(const juce::String& value, std::initializer_list<const char*> tokens)
{
    return hasAny(value, tokens);
}

struct ParameterRank
{
    juce::String role = "advanced";
    float score = 0.10f;
    int danger = 0;
    juce::String reason = "Thông số nâng cao do plug-in công bố";
};

ParameterRank rankFor(PluginCategory category, const EffectParameterDescriptor& descriptor)
{
    const auto value = normalise(descriptor.groupPath + descriptor.name + descriptor.identifier);
    ParameterRank rank;
    if (parameterHas(value, { "bypass", "program", "preset", "midilearn", "hostsync", "version" }))
        return { "internal", 0.0f, 0, "Điều khiển hệ thống, không phù hợp với núm biểu diễn" };

    const auto isMix = parameterHas(value, { "drywet", "wetdry", "mix", "blend", "amount" });
    const auto isOutput = parameterHas(value, { "outputgain", "outgain", "outputlevel", "mastergain" });
    if (isMix) return { "mix", 0.90f, 0, "Tỷ lệ hiệu ứng là điều khiển biểu diễn quan trọng" };
    if (isOutput) return { "output_level", 0.76f, 1, "Mức ra hữu ích nhưng cần giới hạn an toàn" };

    switch (category)
    {
        case PluginCategory::pitchCorrection:
            if (parameterHas(value, { "scaleroot", "rootnote", "keyroot", "keysignature", "musicalkey", "scaletype" })
                || value == "root" || value == "key" || value == "scale" || value == "mode")
                return { "managed_by_autokey", 0.02f, 0, "Key/Scale được AutoKey quản lý tự động" };
            if (parameterHas(value, { "retunespeed", "retune", "speed" }))
                return { "retune_speed", 1.00f, 0, "Điều khiển tốc độ hiệu chỉnh cao độ" };
            if (parameterHas(value, { "humanize", "humanise" }))
                return { "humanize", 0.96f, 0, "Giữ chuyển động tự nhiên của những nốt dài" };
            if (parameterHas(value, { "flextune", "flex" }))
                return { "flex_tune", 0.93f, 0, "Điều khiển độ linh hoạt quanh cao độ đúng" };
            if (parameterHas(value, { "tracking", "sensitivity", "detector" }))
                return { "tracking", 0.86f, 0, "Điều chỉnh độ nhạy bắt cao độ" };
            if (parameterHas(value, { "formant", "throat" }))
                return { "formant", 0.84f, 0, "Điều khiển màu giọng khi chỉnh cao độ" };
            if (parameterHas(value, { "vibrato" }))
                return { "vibrato", 0.72f, 0, "Điều khiển lượng vibrato của bộ tune" };
            break;
        case PluginCategory::equalizer:
        {
            const auto bandParameter = parameterHas(value, { "band", "node" })
                && parameterHas(value, { "frequency", "freq", "gain", "quality", "q", "slope", "used", "enable" });
            if (bandParameter)
                return { "eq_band", 0.18f, 0, "Band EQ nên chỉnh trực tiếp trên analyzer" };
            if (parameterHas(value, { "dynamicrange", "dynrange" }))
                return { "dynamic_range", 0.78f, 0, "Phạm vi dynamic EQ phù hợp để biểu diễn" };
            if (parameterHas(value, { "tilt", "brightness", "tone" }))
                return { "tone", 0.80f, 0, "Điều khiển màu âm tổng quát" };
            break;
        }
        case PluginCategory::dynamics:
            if (parameterHas(value, { "threshold" })) return { "threshold", 1.00f, 0, "Ngưỡng xử lý dynamics chính" };
            if (parameterHas(value, { "ratio" })) return { "ratio", 0.94f, 0, "Cường độ nén chính" };
            if (parameterHas(value, { "attack" })) return { "attack", 0.89f, 0, "Định hình transient đầu vào" };
            if (parameterHas(value, { "release" })) return { "release", 0.87f, 0, "Thời gian hồi của bộ nén" };
            if (parameterHas(value, { "makeup" })) return { "makeup_gain", 0.82f, 1, "Bù mức âm sau khi nén" };
            break;
        case PluginCategory::reverb:
            if (parameterHas(value, { "returnlevel", "wetlevel" })) return { "level", 0.84f, 0, "Mức trả về của reverb" };
            if (parameterHas(value, { "decay", "rt60", "reverbtime" })) return { "decay", 1.00f, 0, "Độ dài không gian reverb" };
            if (parameterHas(value, { "predelay" })) return { "pre_delay", 0.90f, 0, "Khoảng tách giọng khỏi đuôi reverb" };
            if (parameterHas(value, { "size", "roomsize" })) return { "size", 0.86f, 0, "Kích thước không gian mô phỏng" };
            if (parameterHas(value, { "damping", "highcut", "lowcut", "tone" })) return { "tone", 0.80f, 0, "Màu âm của đuôi reverb" };
            break;
        case PluginCategory::delay:
            if (parameterHas(value, { "feedback", "regeneration", "repeat" })) return { "feedback", 0.96f, 2, "Số lần lặp; cần giới hạn chống feedback" };
            if (parameterHas(value, { "delaytime", "synctime", "time" })) return { "delay_time", 0.94f, 0, "Thời gian lặp chính" };
            if (parameterHas(value, { "ducking", "duck" })) return { "ducking", 0.82f, 0, "Giữ giọng rõ khi delay hoạt động" };
            if (parameterHas(value, { "filter", "highcut", "lowcut", "tone" })) return { "tone", 0.78f, 0, "Màu âm của tiếng lặp" };
            break;
        case PluginCategory::saturation:
            if (parameterHas(value, { "drive", "saturation", "distortion", "input" })) return { "drive", 1.00f, 1, "Lượng kích thích/saturation chính" };
            if (parameterHas(value, { "character", "style", "mode" })) return { "character", 0.84f, 0, "Chọn đặc tính màu saturation" };
            if (parameterHas(value, { "tone", "color", "colour", "brightness" })) return { "tone", 0.80f, 0, "Màu âm của saturation" };
            break;
        case PluginCategory::deEsser:
            if (parameterHas(value, { "threshold" })) return { "threshold", 1.00f, 0, "Ngưỡng bắt âm gió chính" };
            if (parameterHas(value, { "frequency", "freq" })) return { "frequency", 0.91f, 0, "Vùng tần số âm gió cần xử lý" };
            if (parameterHas(value, { "range", "reduction", "amount" })) return { "range", 0.88f, 0, "Mức giảm âm gió tối đa" };
            break;
        case PluginCategory::modulation:
            if (parameterHas(value, { "rate", "speed" })) return { "rate", 0.94f, 0, "Tốc độ modulation" };
            if (parameterHas(value, { "depth" })) return { "depth", 0.92f, 0, "Độ sâu modulation" };
            if (parameterHas(value, { "feedback" })) return { "feedback", 0.74f, 2, "Feedback modulation cần giới hạn an toàn" };
            break;
        case PluginCategory::imaging:
            if (parameterHas(value, { "width", "stereowidth", "spread" })) return { "width", 1.00f, 1, "Độ rộng stereo tổng thể" };
            if (parameterHas(value, { "monobass", "bassmono" })) return { "mono_bass", 0.86f, 0, "Giữ dải trầm ổn định ở mono" };
            if (parameterHas(value, { "balance", "pan" })) return { "balance", 0.72f, 0, "Cân bằng ảnh stereo" };
            break;
        case PluginCategory::utility:
            if (parameterHas(value, { "gain", "trim", "level" })) return { "level", 0.88f, 1, "Mức gain/trim chính" };
            if (parameterHas(value, { "balance", "pan" })) return { "balance", 0.76f, 0, "Cân bằng kênh" };
            break;
        case PluginCategory::unknown: break;
    }

    const auto semantic = PluginSemanticMapper::classify(descriptor);
    if (semantic == PluginParameterSemantic::amount) return { "amount", 0.72f, 0, "Lượng hiệu ứng tổng quát" };
    if (semantic == PluginParameterSemantic::tone) return { "tone", 0.68f, 0, "Màu âm tổng quát" };
    if (semantic == PluginParameterSemantic::level) return { "level", 0.62f, 1, "Mức âm tổng quát" };
    return rank;
}

SmartMacroTarget makeTarget(const EffectParameterDescriptor& descriptor, PluginParameterSemantic semantic)
{
    auto target = SmartMacroTarget { descriptor.identifier, descriptor.name, semantic };
    switch (semantic)
    {
        case PluginParameterSemantic::delayFeedback: target.maximum = 0.65f; break;
        case PluginParameterSemantic::level:         target.maximum = 0.80f; break;
        case PluginParameterSemantic::amount:        target.maximum = 0.85f; break;
        case PluginParameterSemantic::dynamics:      target.minimum = 0.15f; target.maximum = 0.78f; break;
        default: break;
    }
    return target;
}

const EffectParameterDescriptor* firstWith(const std::vector<EffectParameterDescriptor>& parameters,
                                           PluginParameterSemantic wanted)
{
    const auto found = std::find_if(parameters.begin(), parameters.end(), [wanted] (const auto& parameter)
    {
        return PluginSemanticMapper::classify(parameter) == wanted;
    });
    return found == parameters.end() ? nullptr : &*found;
}

void addIfPresent(SmartMacroProposal& proposal, const EffectParameterDescriptor* parameter,
                  PluginParameterSemantic semantic)
{
    if (parameter == nullptr || parameter->identifier.isEmpty()) return;
    proposal.targets.push_back(makeTarget(*parameter, semantic));
}
}

PluginParameterSemantic PluginSemanticMapper::classify(const EffectParameterDescriptor& parameter)
{
    const auto name = normalise(parameter.name + parameter.identifier);
    if (hasAny(name, { "bypass", "enable", "onoff" })) return PluginParameterSemantic::unknown;
    if (hasAny(name, { "feedback", "repeat", "regeneration" })) return PluginParameterSemantic::delayFeedback;
    if (hasAny(name, { "decay", "rt60", "reverbtime", "reverberationtime" })) return PluginParameterSemantic::reverbTime;
    if (hasAny(name, { "delaytime", "delay", "synctime" })) return PluginParameterSemantic::delayTime;
    if (hasAny(name, { "retunespeed", "retune", "humanize", "flextune", "tracking" })) return PluginParameterSemantic::vocalTuning;
    if (hasAny(name, { "threshold", "ratio", "makeup", "makeupgain", "compress", "drive" })) return PluginParameterSemantic::dynamics;
    if (hasAny(name, { "highcut", "lowcut", "damping", "tone", "brightness", "filter" })) return PluginParameterSemantic::tone;
    if (hasAny(name, { "send", "return", "output", "outgain", "volume", "level", "gain" })) return PluginParameterSemantic::level;
    if (hasAny(name, { "drywet", "mix", "wet", "blend", "amount" })) return PluginParameterSemantic::amount;
    return PluginParameterSemantic::unknown;
}

juce::String PluginSemanticMapper::displayName(PluginParameterSemantic semantic)
{
    switch (semantic)
    {
        case PluginParameterSemantic::amount: return "Amount";
        case PluginParameterSemantic::level: return "Level";
        case PluginParameterSemantic::reverbTime: return "Space";
        case PluginParameterSemantic::delayFeedback: return "Echo";
        case PluginParameterSemantic::delayTime: return "Delay Time";
        case PluginParameterSemantic::tone: return "Tone";
        case PluginParameterSemantic::dynamics: return "Dynamics";
        case PluginParameterSemantic::vocalTuning: return "Vocal Tune";
        case PluginParameterSemantic::unknown: break;
    }
    return "Unassigned";
}

juce::String PluginSemanticMapper::categoryName(PluginCategory category)
{
    switch (category)
    {
        case PluginCategory::pitchCorrection: return "Pitch Correction";
        case PluginCategory::equalizer: return "Equalizer";
        case PluginCategory::dynamics: return "Dynamics";
        case PluginCategory::reverb: return "Reverb";
        case PluginCategory::delay: return "Delay";
        case PluginCategory::saturation: return "Saturation";
        case PluginCategory::deEsser: return "De-Esser";
        case PluginCategory::modulation: return "Modulation";
        case PluginCategory::imaging: return "Stereo Imaging";
        case PluginCategory::utility: return "Utility";
        case PluginCategory::unknown: break;
    }
    return "Other";
}

std::vector<RankedPluginParameter> PluginSemanticMapper::rankParameters(
    const juce::String& pluginName, const std::vector<EffectParameterDescriptor>& parameters,
    size_t maximumRecommended)
{
    const auto category = categoryFor(normalise(pluginName));
    std::vector<RankedPluginParameter> ranked;
    ranked.reserve(parameters.size());
    for (const auto& descriptor : parameters)
    {
        const auto safe = descriptor.stableIdentifier && descriptor.automatable && ! descriptor.readOnly;
        const auto rank = rankFor(category, descriptor);
        ranked.push_back({ descriptor, category, rank.role, rank.score, false, safe,
                           rank.danger, rank.reason });
    }
    std::stable_sort(ranked.begin(), ranked.end(), [] (const auto& left, const auto& right)
    {
        if (left.safeForMacro != right.safeForMacro) return left.safeForMacro;
        if (left.importance != right.importance) return left.importance > right.importance;
        return left.descriptor.name.compareIgnoreCase(right.descriptor.name) < 0;
    });
    size_t count = 0;
    for (auto& parameter : ranked)
        if (parameter.safeForMacro && parameter.importance >= 0.68f
            && parameter.role != "managed_by_autokey" && count < maximumRecommended)
        {
            parameter.recommended = true;
            ++count;
        }
    return ranked;
}

SmartMacroProposal PluginSemanticMapper::propose(const juce::String& pluginName,
                                                  const std::vector<EffectParameterDescriptor>& parameters)
{
    const auto plugin = normalise(pluginName);
    auto proposal = SmartMacroProposal {};
    std::vector<EffectParameterDescriptor> usable;
    for (const auto& parameter : rankParameters(pluginName, parameters))
        if (parameter.recommended && parameter.safeForMacro)
            usable.push_back(parameter.descriptor);

    if (isReverb(plugin))
    {
        proposal.displayName = "Vocal Space";
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::level), PluginParameterSemantic::level);
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::amount), PluginParameterSemantic::amount);
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::reverbTime), PluginParameterSemantic::reverbTime);
        proposal.confidence = proposal.targets.size() >= 2 ? 0.92f : 0.68f;
    }
    else if (isDelay(plugin))
    {
        proposal.displayName = "Lead Delay";
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::level), PluginParameterSemantic::level);
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::delayFeedback), PluginParameterSemantic::delayFeedback);
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::tone), PluginParameterSemantic::tone);
        proposal.confidence = proposal.targets.size() >= 2 ? 0.90f : 0.66f;
    }
    else if (isDynamics(plugin))
    {
        proposal.displayName = "Vocal Dynamics";
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::dynamics), PluginParameterSemantic::dynamics);
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::level), PluginParameterSemantic::level);
        proposal.confidence = proposal.targets.size() >= 2 ? 0.84f : 0.62f;
    }
    else if (const auto* tuning = firstWith(usable, PluginParameterSemantic::vocalTuning); tuning != nullptr)
    {
        proposal.displayName = "Vocal Tune";
        addIfPresent(proposal, tuning, PluginParameterSemantic::vocalTuning);
        addIfPresent(proposal, firstWith(usable, PluginParameterSemantic::amount), PluginParameterSemantic::amount);
        proposal.confidence = 0.80f;
    }
    else
    {
        proposal.displayName = categoryName(categoryFor(plugin));
        for (const auto& parameter : usable)
        {
            if (proposal.targets.size() >= 3) break;
            proposal.targets.push_back(makeTarget(parameter, classify(parameter)));
        }
        proposal.confidence = proposal.targets.empty() ? 0.0f : 0.76f;
    }

    proposal.needsReview = proposal.targets.empty() || proposal.confidence < 0.70f;
    if (proposal.targets.empty()) proposal.displayName = "Unassigned";
    return proposal;
}
