from voice.stt import wait_for_wake_word

print("Say 'Hey REYA' to continue...")
if wait_for_wake_word():
    print("✅ Wake word detected!")
else:
    print("❌ Wake word NOT detected.")
