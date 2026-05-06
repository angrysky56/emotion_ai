import os
from pathlib import Path

import memvid_sdk


def test_memvid_v2():
    print("Testing memvid-sdk v2...")

    mv2_path = "test_memory.mv2"
    if os.path.exists(mv2_path):
        os.remove(mv2_path)

    try:
        # 1. Create a memory
        with memvid_sdk.create(mv2_path, enable_vec=True, enable_lex=True) as mv:
            print(f"✅ Created/Opened {mv2_path}")

            # 2. Put some data
            mv.put(
                title="Test Entry",
                labels=["test", "aura"],
                metadata={"user": "ty", "emotion": "happy"},
                text="Aura is an advanced emotional AI system designed by Ty.",
            )
            print("✅ Put data into memory")

            # 3. Find data
            results = mv.find("Who designed Aura?")
            print(f"✅ Find results: {len(results.get('hits', []))} hits")
            for hit in results.get("hits", []):
                print(f"  - Hit: {hit.get('snippet')} (Score: {hit.get('score')})")

            # 4. Ask a question (if LLM is configured, but let's check context retrieval)
            # We can use context_only=True to avoid needing an LLM key for testing
            try:
                ans = mv.ask("Who is Ty?", context_only=True)
                print(
                    f"✅ Ask (context_only) successful: {len(ans.get('hits', []))} sources"
                )
            except Exception as e:
                print(f"❌ Ask failed (expected if no LLM): {e}")

        # 5. Check stats
        with memvid_sdk.use("basic", mv2_path) as mv:
            stats = mv.stats()
            print(f"✅ Stats: {stats}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if os.path.exists(mv2_path):
            os.remove(mv2_path)


if __name__ == "__main__":
    test_memvid_v2()
