use std::collections::HashMap;
use crate::command_protocol::CommandMode;

pub struct SkillManager {
    skills: HashMap<CommandMode, String>,
}

impl SkillManager {
    pub fn new() -> Self {
        let mut skills = HashMap::new();
        
        skills.insert(CommandMode::Think, include_str!("./skills/think/SKILL.md").to_string());
        // More will be added
        
        Self { skills }
    }

    pub fn get_skill_directive(&self, mode: &CommandMode) -> Option<String> {
        self.skills.get(mode).cloned()
    }
}
