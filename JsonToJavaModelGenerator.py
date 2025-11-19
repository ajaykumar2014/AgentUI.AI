import json
class JsonToJavaModelGenerator:
    """
    ===============================================
    📌 JSON → Java Model Class Generator (Lombok)
    ===============================================

    This utility converts a JSON structure into a Java POJO class.
    - Supports nested objects (recursively generates inner classes).
    - Supports arrays (generates List<T>).
    - Maps JSON types to Java types:
        string  -> String
        number  -> int / double
        boolean -> boolean
        object  -> separate Java class
        array   -> List<T>

    ✅ Generates Lombok annotations:
       @Data
       @Builder
       @NoArgsConstructor
       @AllArgsConstructor
    ===============================================
    """

    def __init__(self, class_name="Root"):
        self.class_name = class_name
        self.generated_classes = {}

    def _to_camel_case(self, s):
        parts = s.replace("-", "_").split("_")
        return parts[0].lower() + ''.join(x.title() for x in parts[1:])

    def _capitalize(self, s):
        return s[0].upper() + s[1:]

    def _json_type_to_java(self, key, value):
        if isinstance(value, str):
            return "String"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "double"
        elif isinstance(value, dict):
            class_name = self._capitalize(key)
            self._generate_class(class_name, value)
            return class_name
        elif isinstance(value, list) and value:
            elem_type = self._json_type_to_java(key, value[0])
            return f"List<{elem_type}>"
        else:
            return "Object"

    def _generate_class(self, class_name, json_dict):
        if class_name in self.generated_classes:
            return

        imports = set()
        fields = []

        for key, value in json_dict.items():
            field_name = self._to_camel_case(key)
            java_type = self._json_type_to_java(key, value)

            if java_type.startswith("List"):
                imports.add("import java.util.List;")

            fields.append(f"    private {java_type} {field_name};")

        class_code = [
            "import lombok.Data;",
            "import lombok.Builder;",
            "import lombok.NoArgsConstructor;",
            "import lombok.AllArgsConstructor;"
        ]

        if imports:
            class_code.extend(list(imports))

        class_code.append("")
        class_code.append("@Data")
        class_code.append("@Builder")
        class_code.append("@NoArgsConstructor")
        class_code.append("@AllArgsConstructor")
        class_code.append(f"public class {class_name} {{")
        class_code.extend(fields)
        class_code.append("}")

        self.generated_classes[class_name] = "\n".join(class_code)

    def generate(self, json_data):
        if isinstance(json_data, str):
            json_data = json.loads(json_data)

        self._generate_class(self.class_name, json_data)
        return "\n\n".join(self.generated_classes.values())


# ------------------------------
# Example Usage
# ------------------------------
if __name__ == "__main__":
    sample_json = {
        "id": 1,
        "name": "Ajay",
        "email": "ajay@example.com",
        "isActive": True,
        "salary": 55000.75,
        "address": {
            "street": "MG Road",
            "city": "Bangalore",
            "zip": 560001
        },
        "skills": ["Java", "Python", "Kafka"]
    }

    generator = JsonToJavaModelGenerator("Employee")
    java_code = generator.generate(sample_json)

    print(java_code)
