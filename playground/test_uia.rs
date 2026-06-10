use uiautomation::types::ControlType;

fn main() {
    let ct = ControlType::Button;
    // let's try ct.0 or ct as i32
    let val_as: i32 = ct as i32;
    println!("val_as: {}", val_as);
}
