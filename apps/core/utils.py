from django.utils.text import slugify


def generate_unique_slug(instance, source_field, slug_field="slug"):
    """
    Generate a unique slug for a model instance.

    Example:
    title = "Monaco Grand Prix Preview"
    slug  = "monaco-grand-prix-preview"

    If that exists:
    slug = "monaco-grand-prix-preview-2"
    """

    source_value = getattr(instance, source_field)
    base_slug = slugify(source_value)

    if not base_slug:
        base_slug = "item"

    slug = base_slug
    model_class = instance.__class__
    counter = 2

    queryset = model_class.objects.filter(**{slug_field: slug})

    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

        queryset = model_class.objects.filter(**{slug_field: slug})

        if instance.pk:
            queryset = queryset.exclude(pk=instance.pk)

    return slug
