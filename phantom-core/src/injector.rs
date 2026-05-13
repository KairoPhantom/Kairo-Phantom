use std::time::Duration;
use tokio::time::sleep;
use tokio_util::sync::CancellationToken;
use rand::Rng;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SpeedProfile {
    Ghost,
    FastHuman,
    Natural,
    Readable,
}

pub struct HumanizedInjector {
    profile: SpeedProfile,
    char_count_since_pause: usize,
    word_length: usize,
    word_char_index: usize,
}

impl HumanizedInjector {
    pub fn new(delay_ms: u64) -> Self {
        let profile = if delay_ms == 0 {
            SpeedProfile::Ghost
        } else if delay_ms < 30 {
            SpeedProfile::FastHuman
        } else if delay_ms < 100 {
            SpeedProfile::Natural
        } else {
            SpeedProfile::Readable
        };
        
        Self {
            profile,
            char_count_since_pause: 0,
            word_length: 0,
            word_char_index: 0,
        }
    }

    /// Simulate injecting a character with appropriate rhythm delays.
    pub async fn inject_char(&mut self, c: char, cancel: &CancellationToken) -> bool {
        if cancel.is_cancelled() {
            // Finish current word before stopping (if natural/readable)
            if c.is_whitespace() || self.profile == SpeedProfile::Ghost {
                return false; // Stop injection
            }
        }

        // Calculate delay
        let delay = self.calculate_delay(c);

        // Simulate typing the character (in real app, use Enigo)
        // enigo.key_sequence(&c.to_string());
        
        if delay.as_millis() > 0 {
            sleep(delay).await;
        }

        true // Continue injection
    }

    fn calculate_delay(&mut self, c: char) -> Duration {
        if self.profile == SpeedProfile::Ghost {
            return Duration::from_millis(0);
        }

        let mut rng = rand::thread_rng();
        let mut delay_ms = 0;

        match self.profile {
            SpeedProfile::FastHuman => {
                delay_ms = rng.gen_range(30..=60) + rng.gen_range(0..=30) - 15;
            }
            SpeedProfile::Natural => {
                delay_ms = rng.gen_range(60..=120);
            }
            SpeedProfile::Readable => {
                delay_ms = rng.gen_range(100..=150); // slower baseline
            }
            _ => {}
        }

        // Word boundary logic
        if c.is_whitespace() {
            if self.profile == SpeedProfile::Natural || self.profile == SpeedProfile::Readable {
                delay_ms += 150;
            }
            self.word_length = 0;
            self.word_char_index = 0;
            
            if c == '\n' {
                delay_ms += 300;
            }
        } else {
            self.word_char_index += 1;
            // We can't know full word length ahead without buffering, 
            // but we assume if index > 4 we might slow down.
            if self.word_char_index >= 5 && self.word_char_index <= 8 {
                delay_ms += 40; // cognitive load
            }
        }

        // Punctuation
        if c == '.' || c == ',' {
            delay_ms += 200;
        } else if c == '!' || c == '?' || c == ';' || c == ':' {
            delay_ms += 50;
        }

        // Random micro-pauses (1 in 40 chars)
        self.char_count_since_pause += 1;
        if self.char_count_since_pause > rng.gen_range(30..50) {
            delay_ms += rng.gen_range(400..=800);
            self.char_count_since_pause = 0;
        }

        // Ensure no negative delays
        let final_ms = delay_ms.max(0) as u64;
        Duration::from_millis(final_ms)
    }

    pub async fn inject_stream(&mut self, text: &str, cancel: &CancellationToken) {
        for c in text.chars() {
            if !self.inject_char(c, cancel).await {
                break;
            }
        }
    }

    pub fn type_text(&self, text: &str) {
        // Synchronous wrapper for legacy calls
        println!("Typing (sync): {}", text);
    }

    pub fn erase_prompt(&self, count: usize) {
        println!("Erasing {} characters...", count);
    }

    pub fn escape_ribbon_mode(&self) {
        println!("Escaping ribbon mode...");
    }

    pub fn undo_ghost_char(&self) {
        println!("Undoing ghost char...");
    }

    pub fn inject_via_clipboard(&self, text: &str) -> bool {
        println!("Injecting via clipboard: {}", text);
        true
    }
}
