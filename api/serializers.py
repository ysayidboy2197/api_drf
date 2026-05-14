from rest_framework import serializers
from .models import Driver, Car, Fine


# ─────────────────────────────────────────
# 1. ODDIY (FLAT) SERIALIZERLAR
# ─────────────────────────────────────────

class FineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fine
        fields = ['id', 'amount', 'date', 'car']


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['id', 'brand', 'license_plate']


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['id', 'first_name', 'last_name']


# ─────────────────────────────────────────
# 2. NESTED READ-ONLY SERIALIZERLAR
#    (GET so'rovlarida ichma-ich ko'rsatish)
# ─────────────────────────────────────────

class FineNestedSerializer(serializers.ModelSerializer):
    """Fine — faqat o'qish uchun"""
    class Meta:
        model = Fine
        fields = ['id', 'amount', 'date']


class CarWithFinesSerializer(serializers.ModelSerializer):
    """Car ichida unga tegishli barcha Finelar ko'rinadi"""
    fines = FineNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Car
        fields = ['id', 'brand', 'license_plate', 'fines']


class DriverWithCarsSerializer(serializers.ModelSerializer):
    """Driver ichida uning Carlari, har bir Car ichida Finelari"""
    cars = CarWithFinesSerializer(many=True, read_only=True)

    class Meta:
        model = Driver
        fields = ['id', 'first_name', 'last_name', 'cars']


# ─────────────────────────────────────────
# 3. NESTED WRITE SERIALIZER
#    (POST/PUT da bir vaqtda yaratish)
# ─────────────────────────────────────────

class FineWritableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fine
        fields = ['amount', 'date']


class CarWritableSerializer(serializers.ModelSerializer):
    """Car yaratishda unga Fine larni ham birga yuborsa bo'ladi"""
    fines = FineWritableSerializer(many=True, required=False)

    class Meta:
        model = Car
        fields = ['driver', 'brand', 'license_plate', 'fines']

    def create(self, validated_data):
        fines_data = validated_data.pop('fines', [])   # Finelarni ajratib olamiz
        car = Car.objects.create(**validated_data)       # Avval Car saqlanadi
        for fine_data in fines_data:
            Fine.objects.create(car=car, **fine_data)   # Keyin har bir Fine
        return car

    def update(self, instance, validated_data):
        fines_data = validated_data.pop('fines', [])
        # Car maydonlarini yangilaymiz
        instance.brand = validated_data.get('brand', instance.brand)
        instance.license_plate = validated_data.get('license_plate', instance.license_plate)
        instance.save()
        # Eski finelarni o'chirib, yangisini yozamiz (oddiy strategiya)
        instance.fines.all().delete()
        for fine_data in fines_data:
            Fine.objects.create(car=instance, **fine_data)
        return instance


class DriverWritableSerializer(serializers.ModelSerializer):
    """Driver + uning Carlari + har bir Car ning Finelari — hammasi bitta POST da"""
    cars = CarWritableSerializer(many=True, required=False)

    class Meta:
        model = Driver
        fields = ['first_name', 'last_name', 'cars']

    def create(self, validated_data):
        cars_data = validated_data.pop('cars', [])
        driver = Driver.objects.create(**validated_data)
        for car_data in cars_data:
            fines_data = car_data.pop('fines', [])
            car = Car.objects.create(driver=driver, **car_data)
            for fine_data in fines_data:
                Fine.objects.create(car=car, **fine_data)
        return driver


# ─────────────────────────────────────────
# 4. SerializerMethodField BILAN NESTED
#    (hisoblangan maydon qo'shish)
# ─────────────────────────────────────────

class DriverSummarySerializer(serializers.ModelSerializer):
    """Driver uchun qo'shimcha hisoblangan maydonlar"""
    full_name       = serializers.SerializerMethodField()
    total_cars      = serializers.SerializerMethodField()
    total_fines_sum = serializers.SerializerMethodField()
    cars            = CarWithFinesSerializer(many=True, read_only=True)

    class Meta:
        model = Driver
        fields = ['id', 'full_name', 'total_cars', 'total_fines_sum', 'cars']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_total_cars(self, obj):
        return obj.cars.count()

    def get_total_fines_sum(self, obj):
        total = sum(
            fine.amount
            for car in obj.cars.all()
            for fine in car.fines.all()
        )
        return total