from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.validation import validate_schema


class SchemaContractTests(SimpleTestCase):
    def test_full_schema_describes_lists_and_envelopes(self):
        schema = SchemaGenerator().get_schema(public=True)
        validate_schema(schema)
        schemas = schema["components"]["schemas"]
        paths = schema["paths"]

        def body(path, method, code):
            ref = paths[path][method]["responses"][code]["content"]["application/json"][
                "schema"
            ]["$ref"]
            return schemas[ref.split("/")[-1]]

        self.assertEqual(
            body("/api/racing/drivers/", "get", "200")["properties"]["results"]["type"],
            "array",
        )
        self.assertIn("data", body("/api/racing/drivers/", "post", "201")["properties"])
        self.assertEqual(
            body("/api/users/favorites/drivers/", "get", "200")["properties"]["data"][
                "type"
            ],
            "array",
        )
        self.assertIn("data", body("/api/users/me/", "get", "200")["properties"])
        self.assertNotIn("post", paths["/api/content/articles/featured/"])
