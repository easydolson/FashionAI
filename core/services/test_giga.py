import sys
print(sys.path)

# from gigachat import GigaChat
#
# try:
#     with GigaChat(
#         credentials="MDE5ZTUzY2MtZjEwOC03ZGY4LWIyMDUtNWE1YTg1YjNlYzZjOjgyMGE2ODdhLTQzY2ItNGMyYy1iM2MwLTEzYTQwMGI1YWVjYg==",
#         scope="GIGACHAT_API_PERS",
#         verify_ssl_certs=False,
#         timeout=30.0
#     ) as giga:
#         response = giga.chat("Привет!")
#         print("✅ GigaChat работает!")
#         print(response.choices[0].message.content)
# except Exception as e:
#     print(f"❌ Ошибка: {e}")