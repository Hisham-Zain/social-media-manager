"""
Style Fine-Tuning System for AgencyOS.

Train personalized LoRA adapters to match client writing styles,
emoji usage, sentence structure, and brand voice.

Features:
- Upload past successful posts to learn style
- Train lightweight LoRA adapters with Unsloth
- Load client-specific adapters at generation time
- Style analysis and metrics
"""

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..config import config


@dataclass
class StyleProfile:
    """Captured writing style characteristics."""

    client_id: str
    name: str

    # Style metrics
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0
    emoji_frequency: float = 0.0  # Emojis per 100 words
    hashtag_frequency: float = 0.0
    question_frequency: float = 0.0  # Questions per post
    exclamation_frequency: float = 0.0

    # Common patterns
    common_emojis: list[str] = field(default_factory=list)
    common_phrases: list[str] = field(default_factory=list)
    common_hashtags: list[str] = field(default_factory=list)

    # Vocabulary
    vocabulary_richness: float = 0.0  # Unique words / total words
    formality_score: float = 0.5  # 0 = casual, 1 = formal

    # Adapter info
    adapter_path: str | None = None
    trained_at: str | None = None
    sample_count: int = 0

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "name": self.name,
            "avg_sentence_length": self.avg_sentence_length,
            "avg_paragraph_length": self.avg_paragraph_length,
            "emoji_frequency": self.emoji_frequency,
            "hashtag_frequency": self.hashtag_frequency,
            "question_frequency": self.question_frequency,
            "exclamation_frequency": self.exclamation_frequency,
            "common_emojis": self.common_emojis,
            "common_phrases": self.common_phrases,
            "common_hashtags": self.common_hashtags,
            "vocabulary_richness": self.vocabulary_richness,
            "formality_score": self.formality_score,
            "adapter_path": self.adapter_path,
            "trained_at": self.trained_at,
            "sample_count": self.sample_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StyleProfile":
        return cls(**data)


class StyleTuner:
    """
    Style Fine-Tuning System.

    Trains lightweight LoRA adapters on client writing samples
    to generate content that matches their unique voice.

    Example:
        tuner = StyleTuner()

        # Add writing samples
        tuner.add_samples("client_abc", [
            "🚀 Just launched our new product! Link in bio ⬇️",
            "Here's what I learned from 10 years in tech...",
            # ... more posts
        ])

        # Train adapter
        tuner.train_adapter("client_abc")

        # Generate in client's style
        content = tuner.generate_styled(
            "client_abc",
            prompt="Write a LinkedIn post about AI trends"
        )
    """

    # Informal vs formal word markers
    INFORMAL_MARKERS = {
        "gonna",
        "wanna",
        "kinda",
        "gotta",
        "ain't",
        "yeah",
        "yep",
        "nope",
        "hey",
        "hi",
        "yo",
        "lol",
        "omg",
        "tbh",
        "imo",
        "btw",
        "ngl",
        "super",
        "totally",
        "awesome",
        "cool",
        "amazing",
        "crazy",
        "insane",
    }

    FORMAL_MARKERS = {
        "therefore",
        "however",
        "furthermore",
        "consequently",
        "moreover",
        "nevertheless",
        "accordingly",
        "subsequently",
        "henceforth",
        "regarding",
        "concerning",
        "pursuant",
        "respectively",
        "hereby",
    }

    def __init__(self, adapters_dir: Path | None = None):
        """Initialize StyleTuner."""
        self.adapters_dir = adapters_dir or Path(config.DATA_DIR) / "style_adapters"
        self.adapters_dir.mkdir(parents=True, exist_ok=True)

        self.samples_dir = self.adapters_dir / "samples"
        self.samples_dir.mkdir(parents=True, exist_ok=True)

        self.profiles_path = self.adapters_dir / "profiles.json"
        self.profiles: dict[str, StyleProfile] = self._load_profiles()

        # Lazy-loaded components
        self._model = None
        self._tokenizer = None
        self._style_graph = None  # StyleGraph for visual style matching

        logger.info("✍️ StyleTuner initialized")

    def _load_profiles(self) -> dict[str, StyleProfile]:
        """Load existing style profiles."""
        if self.profiles_path.exists():
            try:
                with open(self.profiles_path, "r") as f:
                    data = json.load(f)
                return {k: StyleProfile.from_dict(v) for k, v in data.items()}
            except Exception:
                pass
        return {}

    def _save_profiles(self):
        """Save style profiles to disk."""
        data = {k: v.to_dict() for k, v in self.profiles.items()}
        with open(self.profiles_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_samples(
        self,
        client_id: str,
        samples: list[str],
        client_name: str | None = None,
        platform: str = "general",
    ) -> int:
        """
        Add writing samples for a client.

        Args:
            client_id: Unique client identifier.
            samples: List of past posts/content.
            client_name: Human-readable client name.
            platform: Platform these samples are from.

        Returns:
            Total number of samples for this client.
        """
        # Create client samples directory
        client_dir = self.samples_dir / client_id
        client_dir.mkdir(parents=True, exist_ok=True)

        # Save samples
        samples_file = client_dir / f"{platform}_samples.json"
        existing = []
        if samples_file.exists():
            with open(samples_file, "r") as f:
                existing = json.load(f)

        existing.extend(samples)

        with open(samples_file, "w") as f:
            json.dump(existing, f, indent=2)

        # Create or update profile
        if client_id not in self.profiles:
            self.profiles[client_id] = StyleProfile(
                client_id=client_id, name=client_name or client_id
            )

        # Analyze style
        all_samples = self._get_all_samples(client_id)
        self._analyze_style(client_id, all_samples)

        self._save_profiles()

        logger.info(f"✅ Added {len(samples)} samples for {client_id}")
        return len(all_samples)

    def _get_all_samples(self, client_id: str) -> list[str]:
        """Get all samples for a client."""
        client_dir = self.samples_dir / client_id
        if not client_dir.exists():
            return []

        all_samples = []
        for sample_file in client_dir.glob("*.json"):
            try:
                with open(sample_file, "r") as f:
                    all_samples.extend(json.load(f))
            except Exception:
                continue

        return all_samples

    def _analyze_style(self, client_id: str, samples: list[str]):
        """Analyze writing style from samples."""
        if not samples:
            return

        profile = self.profiles[client_id]
        profile.sample_count = len(samples)

        all_words = []
        all_sentences = []
        emoji_count = 0
        hashtag_count = 0
        question_count = 0
        exclamation_count = 0
        emojis = []
        hashtags = []
        informal_count = 0
        formal_count = 0

        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map
            "\U0001f1e0-\U0001f1ff"  # flags
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+",
            flags=re.UNICODE,
        )

        for sample in samples:
            # Extract emojis
            found_emojis = emoji_pattern.findall(sample)
            emojis.extend(found_emojis)
            emoji_count += len(found_emojis)

            # Extract hashtags
            found_hashtags = re.findall(r"#\w+", sample)
            hashtags.extend(found_hashtags)
            hashtag_count += len(found_hashtags)

            # Count questions and exclamations
            question_count += sample.count("?")
            exclamation_count += sample.count("!")

            # Split into sentences
            sentences = re.split(r"[.!?]+", sample)
            sentences = [s.strip() for s in sentences if s.strip()]
            all_sentences.extend(sentences)

            # Extract words
            words = re.findall(r"\b\w+\b", sample.lower())
            all_words.extend(words)

            # Check formality
            for word in words:
                if word in self.INFORMAL_MARKERS:
                    informal_count += 1
                elif word in self.FORMAL_MARKERS:
                    formal_count += 1

        # Calculate metrics
        total_words = len(all_words)
        if total_words > 0:
            profile.emoji_frequency = (emoji_count / total_words) * 100
            profile.hashtag_frequency = (hashtag_count / total_words) * 100
            profile.vocabulary_richness = len(set(all_words)) / total_words

        if len(all_sentences) > 0:
            profile.avg_sentence_length = total_words / len(all_sentences)

        if len(samples) > 0:
            profile.avg_paragraph_length = total_words / len(samples)
            profile.question_frequency = question_count / len(samples)
            profile.exclamation_frequency = exclamation_count / len(samples)

        # Formality score
        total_markers = informal_count + formal_count
        if total_markers > 0:
            profile.formality_score = formal_count / total_markers
        else:
            profile.formality_score = 0.5  # Neutral

        # Common patterns (top 10)
        from collections import Counter

        profile.common_emojis = [e for e, _ in Counter(emojis).most_common(10)]
        profile.common_hashtags = [h for h, _ in Counter(hashtags).most_common(10)]

        # Extract common phrases (2-3 word n-grams)
        phrases = []
        for sample in samples:
            words = sample.split()
            for i in range(len(words) - 1):
                phrases.append(" ".join(words[i : i + 2]))
            for i in range(len(words) - 2):
                phrases.append(" ".join(words[i : i + 3]))

        phrase_counts = Counter(phrases)
        profile.common_phrases = [
            p for p, c in phrase_counts.most_common(20) if c >= 3 and len(p) > 5
        ][:10]

        logger.info(
            f"📊 Analyzed style for {client_id}: {profile.sample_count} samples"
        )

    def train_adapter(
        self,
        client_id: str,
        base_model: str = "unsloth/llama-3-8b-bnb-4bit",
        max_samples: int = 100,
        epochs: int = 3,
    ) -> str | None:
        """
        Train a LoRA adapter for client-specific style.

        Uses Unsloth for efficient fine-tuning on consumer GPUs.

        Args:
            client_id: Client identifier.
            base_model: Base model to adapt.
            max_samples: Maximum training samples.
            epochs: Training epochs.

        Returns:
            Path to trained adapter.
        """
        samples = self._get_all_samples(client_id)

        if len(samples) < 10:
            logger.warning(f"Not enough samples ({len(samples)}), need at least 10")
            return None

        logger.info(f"🔧 Training LoRA adapter for {client_id}...")

        try:
            # Check if Unsloth is available
            import torch
            from datasets import Dataset
            from transformers import TrainingArguments
            from trl import SFTTrainer
            from unsloth import FastLanguageModel, is_bfloat16_supported

            # Load base model with 4-bit quantization
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=base_model,
                max_seq_length=2048,
                dtype=None,  # Auto-detect
                load_in_4bit=True,
            )

            # Add LoRA adapters
            model = FastLanguageModel.get_peft_model(
                model,
                r=16,  # LoRA rank
                target_modules=[
                    "q_proj",
                    "k_proj",
                    "v_proj",
                    "o_proj",
                    "gate_proj",
                    "up_proj",
                    "down_proj",
                ],
                lora_alpha=16,
                lora_dropout=0,
                bias="none",
                use_gradient_checkpointing="unsloth",
                random_state=42,
            )

            # Prepare training data
            profile = self.profiles.get(client_id)
            samples = samples[:max_samples]

            # Create instruction-response pairs
            training_data = []
            for sample in samples:
                # Create various instruction types
                instructions = [
                    f"Write a social media post about: {self._extract_topic(sample)}",
                    f"Create content in {profile.name}'s writing style about: {self._extract_topic(sample)}",
                    "Write an engaging post for my audience.",
                ]

                for instruction in instructions[:1]:  # Use first instruction
                    training_data.append(
                        {
                            "instruction": instruction,
                            "input": "",
                            "output": sample,
                        }
                    )

            # Format for training
            def format_prompt(example):
                return f"""### Instruction:
{example["instruction"]}

### Input:
{example["input"]}

### Response:
{example["output"]}"""

            dataset = Dataset.from_list(training_data)

            # Training arguments
            adapter_output = self.adapters_dir / client_id
            adapter_output.mkdir(parents=True, exist_ok=True)

            trainer = SFTTrainer(
                model=model,
                tokenizer=tokenizer,
                train_dataset=dataset,
                formatting_func=format_prompt,
                max_seq_length=2048,
                args=TrainingArguments(
                    output_dir=str(adapter_output),
                    per_device_train_batch_size=2,
                    gradient_accumulation_steps=4,
                    warmup_steps=5,
                    max_steps=len(training_data) * epochs,
                    learning_rate=2e-4,
                    fp16=not is_bfloat16_supported(),
                    bf16=is_bfloat16_supported(),
                    logging_steps=10,
                    optim="adamw_8bit",
                    weight_decay=0.01,
                    lr_scheduler_type="linear",
                    seed=42,
                ),
            )

            # Train
            trainer.train()

            # Save adapter
            model.save_pretrained(str(adapter_output))
            tokenizer.save_pretrained(str(adapter_output))

            # Update profile
            profile.adapter_path = str(adapter_output)
            profile.trained_at = datetime.now().isoformat()
            self._save_profiles()

            logger.info(f"✅ Adapter trained and saved: {adapter_output}")
            return str(adapter_output)

        except ImportError:
            logger.warning("Unsloth not installed. Using prompt-based style matching.")
            return self._create_prompt_adapter(client_id)
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return None

    def _create_prompt_adapter(self, client_id: str) -> str | None:
        """Create a prompt-based style adapter (fallback when Unsloth unavailable)."""
        profile = self.profiles.get(client_id)
        if not profile:
            return None

        # Create style prompt template
        style_prompt = self._generate_style_prompt(profile)

        # Save as text adapter
        adapter_path = self.adapters_dir / client_id / "style_prompt.txt"
        adapter_path.parent.mkdir(parents=True, exist_ok=True)

        with open(adapter_path, "w") as f:
            f.write(style_prompt)

        profile.adapter_path = str(adapter_path)
        profile.trained_at = datetime.now().isoformat()
        self._save_profiles()

        logger.info(f"✅ Prompt-based adapter created: {adapter_path}")
        return str(adapter_path)

    def _generate_style_prompt(self, profile: StyleProfile) -> str:
        """Generate a style-matching system prompt."""
        # Formality description
        if profile.formality_score < 0.3:
            formality = "very casual and conversational"
        elif profile.formality_score < 0.5:
            formality = "casual but professional"
        elif profile.formality_score < 0.7:
            formality = "professional and polished"
        else:
            formality = "formal and authoritative"

        # Emoji usage
        if profile.emoji_frequency > 5:
            emoji_style = f"Use emojis frequently. Favorite emojis: {' '.join(profile.common_emojis[:5])}"
        elif profile.emoji_frequency > 1:
            emoji_style = f"Use emojis occasionally. Preferred: {' '.join(profile.common_emojis[:3])}"
        else:
            emoji_style = "Minimal emoji usage"

        # Build prompt
        prompt = f"""You are writing as {profile.name}. Match their exact writing style:

STYLE CHARACTERISTICS:
- Tone: {formality}
- Average sentence length: {profile.avg_sentence_length:.0f} words
- Vocabulary richness: {"Varied and sophisticated" if profile.vocabulary_richness > 0.6 else "Accessible and clear"}
- Questions per post: {profile.question_frequency:.1f}
- Exclamations per post: {profile.exclamation_frequency:.1f}

EMOJI & HASHTAG USAGE:
- {emoji_style}
- {"Uses hashtags frequently" if profile.hashtag_frequency > 2 else "Minimal hashtag usage"}
- Common hashtags: {" ".join(profile.common_hashtags[:5]) if profile.common_hashtags else "None specified"}

SIGNATURE PHRASES:
{chr(10).join(f'- "{phrase}"' for phrase in profile.common_phrases[:5]) if profile.common_phrases else "- None identified yet"}

WRITING RULES:
1. Mirror their sentence structure and length
2. Use their typical emoji patterns
3. Maintain their level of formality
4. Include their signature phrases when natural
5. Match their punctuation style (questions: {profile.question_frequency:.1f}/post, exclamations: {profile.exclamation_frequency:.1f}/post)
"""
        return prompt

    def _extract_topic(self, text: str) -> str:
        """Extract likely topic from a post."""
        # Remove emojis and hashtags
        cleaned = re.sub(r"[^\w\s]", "", text)
        cleaned = re.sub(r"#\w+", "", cleaned)

        # Get first sentence or first 50 chars
        sentences = cleaned.split(".")
        topic = sentences[0].strip() if sentences else cleaned[:50]

        return topic[:100]

    def generate_styled(
        self,
        client_id: str,
        prompt: str,
        use_adapter: bool = True,
    ) -> str | None:
        """
        Generate content in client's style.

        Args:
            client_id: Client identifier.
            prompt: Generation prompt.
            use_adapter: Use trained LoRA adapter if available.

        Returns:
            Generated content in client's style.
        """
        profile = self.profiles.get(client_id)
        if not profile:
            logger.warning(f"No profile for {client_id}")
            return None

        try:
            # Check for trained adapter
            if use_adapter and profile.adapter_path:
                adapter_path = Path(profile.adapter_path)

                # Check if it's a LoRA adapter or prompt adapter
                if (adapter_path / "adapter_config.json").exists():
                    return self._generate_with_lora(profile, prompt)
                elif (
                    adapter_path.suffix == ".txt"
                    or (adapter_path / "style_prompt.txt").exists()
                ):
                    return self._generate_with_prompt(profile, prompt)

            # Fallback: Generate style prompt on the fly
            return self._generate_with_prompt(profile, prompt)

        except Exception as e:
            logger.error(f"Styled generation failed: {e}")
            return None

    def _generate_with_lora(self, profile: StyleProfile, prompt: str) -> str | None:
        """Generate using trained LoRA adapter."""
        try:
            from unsloth import FastLanguageModel

            # Load model with adapter
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=profile.adapter_path,
                max_seq_length=2048,
                dtype=None,
                load_in_4bit=True,
            )

            # Enable inference mode
            FastLanguageModel.for_inference(model)

            # Generate
            formatted = f"""### Instruction:
{prompt}

### Input:


### Response:
"""
            inputs = tokenizer(formatted, return_tensors="pt").to("cuda")

            outputs = model.generate(
                **inputs,
                max_new_tokens=500,
                temperature=0.7,
                do_sample=True,
            )

            response = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract generated part
            if "### Response:" in response:
                response = response.split("### Response:")[-1].strip()

            return response

        except Exception as e:
            logger.error(f"LoRA generation failed: {e}")
            return self._generate_with_prompt(profile, prompt)

    def _generate_with_prompt(self, profile: StyleProfile, prompt: str) -> str | None:
        """Generate using style prompt injection."""
        from ..ai.brain import HybridBrain

        brain = HybridBrain()
        style_prompt = self._generate_style_prompt(profile)

        full_prompt = f"""{style_prompt}

USER REQUEST:
{prompt}

Generate content following the exact style described above:"""

        return brain.think(full_prompt)

    def get_profile(self, client_id: str) -> StyleProfile | None:
        """Get style profile for a client."""
        return self.profiles.get(client_id)

    def list_clients(self) -> list[str]:
        """List all clients with style profiles."""
        return list(self.profiles.keys())

    def delete_client(self, client_id: str) -> bool:
        """Delete a client's style profile and adapter."""
        if client_id not in self.profiles:
            return False

        # Remove adapter
        adapter_dir = self.adapters_dir / client_id
        if adapter_dir.exists():
            shutil.rmtree(adapter_dir)

        # Remove samples
        samples_dir = self.samples_dir / client_id
        if samples_dir.exists():
            shutil.rmtree(samples_dir)

        # Remove profile
        del self.profiles[client_id]
        self._save_profiles()

        logger.info(f"🗑️ Deleted style profile for {client_id}")
        return True

    def get_visual_style(
        self,
        reference_image: str | None = None,
        reference_text: str | None = None,
        top_k: int = 5,
        tags: list[str] | None = None,
    ) -> dict:
        """
        Get visual style suggestions using StyleGraph embeddings.

        Args:
            reference_image: Path to a reference image for style matching.
            reference_text: Text description for style matching.
            top_k: Number of similar assets to return.
            tags: Optional tags to filter by.

        Returns:
            Dictionary with matched assets and style recommendations.
        """
        try:
            # Lazy-load StyleGraph
            if self._style_graph is None:
                from .style_graph import StyleGraph

                self._style_graph = StyleGraph()

            # Query by different modalities
            if reference_image:
                similar = self._style_graph.query_style(
                    image_path=reference_image,
                    top_k=top_k,
                )
            elif reference_text:
                similar = self._style_graph.query_style(
                    text_query=reference_text,
                    top_k=top_k,
                )
            elif tags:
                similar = self._style_graph.get_style_by_tags(
                    tags=tags,
                    top_k=top_k,
                )
            else:
                # Return top performers
                similar = self._style_graph.query_style(
                    text_query="high engagement professional content",
                    top_k=top_k,
                )

            # Build style recommendations
            recommendations = {
                "matched_assets": [
                    {
                        "asset_id": s.asset_id,
                        "tags": s.tags,
                        "performance_score": s.performance_score,
                        "asset_type": s.asset_type,
                    }
                    for s in similar
                ],
                "style_notes": [],
            }

            # Aggregate style patterns from top performers
            if similar:
                all_tags = []
                for s in similar:
                    all_tags.extend(s.tags)
                from collections import Counter

                common_tags = Counter(all_tags).most_common(10)
                recommendations["style_notes"] = [
                    f"Common visual elements: {', '.join(t for t, _ in common_tags[:5])}",
                    f"Based on {len(similar)} high-performing assets",
                ]

            return recommendations

        except ImportError:
            logger.warning("StyleGraph not available")
            return {"matched_assets": [], "style_notes": ["StyleGraph unavailable"]}
        except Exception as e:
            logger.error(f"Visual style lookup failed: {e}")
            return {"matched_assets": [], "style_notes": [f"Error: {e}"]}


# Convenience functions
def train_client_style(
    client_id: str, samples: list[str], name: str = None
) -> str | None:
    """Quick function to train a client style adapter."""
    tuner = StyleTuner()
    tuner.add_samples(client_id, samples, client_name=name)
    return tuner.train_adapter(client_id)


def generate_in_style(client_id: str, prompt: str) -> str | None:
    """Quick function to generate content in client's style."""
    tuner = StyleTuner()
    return tuner.generate_styled(client_id, prompt)
