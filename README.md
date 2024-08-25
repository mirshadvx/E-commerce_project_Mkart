"# E-commerce-django" 



<!-- "# E-commerce-django" 


class Gender(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='category_images/', blank=True, null=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(null=True,blank=True)
    status = models.BooleanField(default=True)
    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)    
    logo = models.ImageField(upload_to='brand_images/', blank=True, null=True)

    def __str__(self):
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, unique=True)



class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)                                                                                                      
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    description = models.TextField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True)
    image_1 = models.ImageField(upload_to='product_variant_images/', blank=True, null=True)
    image_2 = models.ImageField(upload_to='product_variant_images/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='product_variant_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.color.name} - {self.sku}






##########################################33

old


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE,null=True,blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)                                                                                                      
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    colors = models.ManyToManyField(Color, related_name='products')
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    image_1 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image_2 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True)

    class Meta:
        unique_together = ('product', 'color')

    def __str__(self):
        return f"{self.product.name} - {self.color.name}"# E-commerce_project_Mkart" 
