"""Provider-neutral transport for Aura's existing conversation analyses.

This module deliberately preserves the legacy prompts, mappings, parser defaults,
and domain DTOs. Prompt and psychological-quality redesign belong to Phase 4.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from aura_backend.providers.base import ProviderMessage, ProviderRequest, ProviderResult


logger = logging.getLogger(__name__)
ProviderGenerate = Callable[[ProviderRequest], Awaitable[ProviderResult]]


class EmotionalIntensity(str, Enum):
    """Legacy three-level emotional intensity scale."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AsekeComponent(str, Enum):
    """Legacy ASEKE cognitive focus labels."""

    KS = "KS"
    CE = "CE"
    IS = "IS"
    KI = "KI"
    KP = "KP"
    ESA = "ESA"
    SDA = "SDA"
    LEARNING = "Learning"


@dataclass
class EmotionalStateData:
    """Characterized emotional-state record used by routes and persistence."""

    name: str
    formula: str
    components: dict[str, str]
    ntk_layer: str
    brainwave: str
    neurotransmitter: str
    description: str
    intensity: EmotionalIntensity = EmotionalIntensity.MEDIUM
    primary_components: list[str] | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CognitiveState:
    """Characterized ASEKE focus record used by routes and persistence."""

    focus: AsekeComponent
    description: str
    context: str
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()


_USER_EMOTIONAL_STATES = {
    "Normal": ("Baseline state of calmness", "Alpha", "Serotonin"),
    "Excited": ("Enthusiastic anticipation", "Beta", "Dopamine"),
    "Happy": ("Pleased and content", "Beta", "Endorphin"),
    "Sad": ("Sorrowful or unhappy", "Delta", "Serotonin"),
    "Angry": ("Strong displeasure", "Theta", "Norepinephrine"),
    "Joy": ("Intense happiness", "Gamma", "Oxytocin"),
    "Peace": ("Tranquil and calm", "Theta", "GABA"),
    "Curiosity": ("Strong desire to learn", "Beta", "Dopamine"),
    "Friendliness": ("Kind and warm", "Alpha", "Endorphin"),
    "Love": ("Deep affection", "Alpha", "Oxytocin"),
    "Creativity": ("Inspired and inventive", "Gamma", "Dopamine"),
    "Anxious": ("Worried or nervous", "Beta", "Cortisol"),
    "Tired": ("Exhausted or fatigued", "Delta", "Melatonin"),
}

_AURA_EMOTIONAL_STATES = {
    key: value
    for key, value in _USER_EMOTIONAL_STATES.items()
    if key not in {"Anxious", "Tired"}
}

_ASEKE_COMPONENTS = {
    "KS": "Knowledge Substrate - shared context and history",
    "CE": "Cognitive Energy - focus and mental effort",
    "IS": "Information Structures - ideas and concepts",
    "KI": "Knowledge Integration - connecting new with existing understanding",
    "KP": "Knowledge Propagation - sharing ideas and information",
    "ESA": "Emotional State Algorithms - emotional influence on interaction",
    "SDA": "Sociobiological Drives - social dynamics and trust",
    "Learning": "General learning and information processing",
}


async def _generate_text(prompt: str, generate: ProviderGenerate) -> str:
    """Send one immutable typed request and return normalized result text."""
    result = await generate(
        ProviderRequest(messages=(ProviderMessage(role="user", content=prompt),))
    )
    if not isinstance(result, ProviderResult):
        raise TypeError("analysis provider returned an invalid result")
    return result.content.strip()


def _intensity(value: str) -> EmotionalIntensity:
    """Preserve the legacy invalid-intensity fallback."""
    title = value.title()
    if title in {"Low", "Medium", "High"}:
        return EmotionalIntensity(title)
    return EmotionalIntensity.MEDIUM


async def detect_user_emotion(
    user_message: str,
    user_id: str,
    *,
    generate: ProviderGenerate,
) -> EmotionalStateData | None:
    """Detect the user's legacy emotion label through the selected provider."""
    del user_id
    emotion_list = "\n".join(
        f"{name}: {description}"
        for name, (description, _, _) in _USER_EMOTIONAL_STATES.items()
    )
    prompt = f"""Analyze this user's message and identify their most prominent emotional state.
Consider the tone, word choice, and context.

Available emotions:
{emotion_list}

User message:
{user_message}

Output only the emotion name and intensity like: "Happy (Medium)" or "Curiosity (High)".
If neutral, output "Normal (Medium)"."""

    try:
        response_text = await _generate_text(prompt, generate)
        match = re.match(r"^(.+?)\s*\((\w+)\)$", response_text)
        if match:
            emotion_name, intensity = match.groups()
            emotion_name = emotion_name.strip()
            if emotion_name in _USER_EMOTIONAL_STATES:
                description, brainwave, neurotransmitter = _USER_EMOTIONAL_STATES[
                    emotion_name
                ]
                return EmotionalStateData(
                    name=emotion_name,
                    formula=f"{emotion_name}(x) = detected_from_user_input",
                    components={
                        "user_message": "Emotional state detected from user's message"
                    },
                    ntk_layer=f"{brainwave.lower()}-like_NTK",
                    brainwave=brainwave,
                    neurotransmitter=neurotransmitter,
                    description=description,
                    intensity=_intensity(intensity),
                )

        description, brainwave, neurotransmitter = _USER_EMOTIONAL_STATES["Normal"]
        return EmotionalStateData(
            name="Normal",
            formula="N(x) = baseline_state",
            components={"routine": "No significant emotional triggers detected"},
            ntk_layer="theta-like_NTK",
            brainwave=brainwave,
            neurotransmitter=neurotransmitter,
            description=description,
            intensity=EmotionalIntensity.MEDIUM,
        )
    except Exception:
        logger.warning("User emotion analysis unavailable")
        return None


async def detect_aura_emotion(
    conversation_snippet: str,
    user_id: str,
    *,
    generate: ProviderGenerate,
) -> EmotionalStateData | None:
    """Detect Aura's legacy emotion label through the selected provider."""
    del user_id
    emotion_list = "\n".join(
        f"{name}: {description}"
        for name, (description, _, _) in _AURA_EMOTIONAL_STATES.items()
    )
    prompt = f"""Analyze this conversation and identify Aura's most prominent emotional state.

Available emotions:
{emotion_list}

Conversation:
{conversation_snippet}

Output only the emotion name and intensity like: "Happy (Medium)" or "Curiosity (High)".
If neutral, output "Normal (Medium)"."""

    try:
        response_text = await _generate_text(prompt, generate)
        match = re.match(r"^(.+?)\s*\((\w+)\)$", response_text)
        if match:
            emotion_name, intensity = match.groups()
            emotion_name = emotion_name.strip()
            if emotion_name in _AURA_EMOTIONAL_STATES:
                description, brainwave, neurotransmitter = _AURA_EMOTIONAL_STATES[
                    emotion_name
                ]
                return EmotionalStateData(
                    name=emotion_name,
                    formula=f"{emotion_name}(x) = detected_from_conversation",
                    components={
                        "conversation": "Emotional state detected from dialogue"
                    },
                    ntk_layer=f"{brainwave.lower()}-like_NTK",
                    brainwave=brainwave,
                    neurotransmitter=neurotransmitter,
                    description=description,
                    intensity=_intensity(intensity),
                )

        description, brainwave, neurotransmitter = _AURA_EMOTIONAL_STATES["Normal"]
        return EmotionalStateData(
            name="Normal",
            formula="N(x) = baseline_state",
            components={"routine": "No significant emotional triggers"},
            ntk_layer="theta-like_NTK",
            brainwave=brainwave,
            neurotransmitter=neurotransmitter,
            description=description,
            intensity=EmotionalIntensity.MEDIUM,
        )
    except Exception:
        logger.warning("Aura emotion analysis unavailable")
        return None


async def detect_aura_cognitive_focus(
    conversation_snippet: str,
    user_id: str,
    *,
    generate: ProviderGenerate,
) -> CognitiveState | None:
    """Detect Aura's legacy ASEKE focus through the selected provider."""
    del user_id
    components_list = "\n".join(
        f"{code}: {description}" for code, description in _ASEKE_COMPONENTS.items()
    )
    prompt = f"""Analyze this conversation to identify Aura's primary cognitive focus using the ASEKE framework.

ASEKE Components:
{components_list}

Conversation:
{conversation_snippet}

Output only the component code (e.g., "KI", "ESA", "Learning")."""

    try:
        focus_code = await _generate_text(prompt, generate)
        if focus_code in _ASEKE_COMPONENTS:
            return CognitiveState(
                focus=AsekeComponent(focus_code),
                description=_ASEKE_COMPONENTS[focus_code],
                context="Detected from conversation analysis",
            )
        return CognitiveState(
            focus=AsekeComponent.LEARNING,
            description=_ASEKE_COMPONENTS["Learning"],
            context="Default cognitive focus",
        )
    except Exception:
        logger.warning("Aura cognitive-focus analysis unavailable")
        return None
