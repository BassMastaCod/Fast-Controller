from typing import Optional
from datetime import datetime
import pytest
from daomodel.fields import Identifier

from fast_controller import Resource
from fast_controller.schema import Schema, schemas, default_schema, input_schema, output_schema, detailed_output_schema


class UserInput(Schema):
    username: str
    email: str
    password: str


class UserOutput(Schema):
    id: int
    username: str
    email: str


class UserDetailedOutput(UserOutput):
    created_at: datetime
    last_login: Optional[datetime] = None


class TestSchemaDecorators:
    """Tests for the schema decorators used to define Resource schemas."""

    def test_predefined_schema_classes(self):
        """Test applying predefined Schema subclasses using decorators."""
        @input_schema(UserInput)
        @detailed_output_schema(UserDetailedOutput)
        class UserResource(Resource):
            pass

        assert UserResource.get_input_schema() == UserInput
        assert UserResource.get_detailed_output_schema() == UserDetailedOutput
        # Check fallbacks: output falls back to default, which falls back to base (Resource/DAOModel)
        assert UserResource.get_output_schema() == UserResource.get_base()

    def test_inline_schema_definitions(self):
        """Test applying schemas defined inline using keyword arguments."""
        @output_schema(id=int, username=str)
        class SimpleResource(Resource):
            pass

        output = SimpleResource.get_output_schema()
        assert issubclass(output, Schema)
        assert output.__name__ == "SimpleResourceOutput"
        assert "id" in output.model_fields
        assert output.model_fields["id"].annotation == int
        assert "username" in output.model_fields
        assert output.model_fields["username"].annotation == str

        # Verify it's a functional Pydantic model
        instance = output(id=1, username="testuser")
        assert instance.id == 1
        assert instance.username == "testuser"

    def test_default_schema_fallback(self):
        """Test that default_schema acts as a fallback for other roles."""
        @default_schema(id=int, name=str)
        class DefaultedResource(Resource):
            pass

        default = DefaultedResource.get_default_schema()
        assert default.__name__ == "DefaultedResourceDefault"

        # All other schemas should fall back to default if not explicitly set
        assert DefaultedResource.get_input_schema() == default
        assert DefaultedResource.get_update_schema() == default
        assert DefaultedResource.get_output_schema() == default
        assert DefaultedResource.get_detailed_output_schema() == default

    def test_bulk_schemas_decorator(self):
        """Test the @schemas decorator for applying multiple schemas at once."""
        @schemas(
            input=UserInput,
            update={'email': Optional[str], 'password': Optional[str]},
            output=UserOutput
        )
        class BulkResource(Resource):
            pass

        assert BulkResource.get_input_schema() == UserInput
        assert BulkResource.get_output_schema() == UserOutput

        update = BulkResource.get_update_schema()
        assert issubclass(update, Schema)
        assert update.__name__ == "BulkResourceUpdate"
        assert update.model_fields["email"].annotation == Optional[str]
        assert update.model_fields["password"].annotation == Optional[str]

    def test_real_looking_usage(self):
        """A test case demonstrating more 'real world' usage with various types."""
        class ProfileInput(Schema):
            display_name: str
            bio: Optional[str] = None
            age: int

        @schemas(
            input=ProfileInput,
            output={
                'id': Identifier[int],
                'display_name': str,
                'is_active': bool
            },
            detailed_output=ProfileInput # Reusing input for detailed output as an example
        )
        class ProfileResource(Resource):
            pass

        assert ProfileResource.get_input_schema() == ProfileInput
        assert ProfileResource.get_detailed_output_schema() == ProfileInput

        output = ProfileResource.get_output_schema()
        assert output.model_fields['id'].annotation == Identifier[int]
        assert output.model_fields['is_active'].annotation == bool

    def test_decorator_validation_errors(self):
        """Test error handling when decorators are used incorrectly."""

        # 1. Applying to a class that is not a Resource (missing setters)
        class NotAResource:
            pass

        with pytest.raises(AttributeError, match='Expected method "set_input_schema" to exist'):
            input_schema(UserInput)(NotAResource)

        # 2. schemas() with unsupported roles
        with pytest.raises(AttributeError, match='does not support schema role "invalid_role"'):
            @schemas(invalid_role=UserInput)
            class InvalidRoleResource(Resource):
                pass

        # 3. Providing both positional schema and inline fields
        with pytest.raises(TypeError, match="received both a schema argument and inline fields"):
            @input_schema(UserInput, extra_field=int)
            class AmbiguousResource(Resource):
                pass

        # 4. Providing neither schema nor inline fields
        with pytest.raises(TypeError, match="requires either a Schema subclass or inline field definitions"):
            @input_schema()
            class EmptyResource(Resource):
                pass
