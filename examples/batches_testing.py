import base64

from gigachat import GigaChat

giga = GigaChat(
    scope="GIGACHAT_API_CORP",
    credentials="MDE5OWI4ZTUtNzRlYy03MTA1LWE0YzgtMTdjZjkxYzAzZWI1OjgyZTgxM2RlLTVjZTYtNDFmOC1hYzg5LWYxZDNlNGNhMWVmMw==",
    # user="knkrestnikov",
    # password="G8HmQRJ51CtT",
    # base_url="https://gigachat.sberdevices.ru/v1",
    verify_ssl_certs=False,
)
with open("batch_file.jsonl", "rb") as f:
    data = f.read()
print(type(data))
# batch_creation = giga.create_batch(data, method="chat_completions")
# print(batch_creation)
my_batch = giga.get_batches(batch_id="ea72ef5a-3460-4174-9219-6901483ecdf3")
print(my_batch)


output_file = giga.get_file_content("943cab73-d238-49e3-8247-2b0c002c642a")
print(output_file)
print(output_file.content)
decoded = base64.b64decode(output_file.content)
print(decoded)
with open("answers.jsonl", "wb") as f:
    f.write(decoded)
