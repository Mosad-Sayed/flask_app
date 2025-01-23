$(document).ready(function () {
    // إضافة مكون جديد
    $('#add_ingredient').click(function () {
        const newIngredient = $('.ingredient').first().clone();
        newIngredient.find('input').val('');
        newIngredient.find('.nutrition-info span').text('-');
        $('#ingredients').append(newIngredient);
    });

    // إزالة مكون
    $(document).on('click', '.remove_ingredient', function () {
        if ($('.ingredient').length > 1) {
            $(this).closest('.ingredient').remove();
        }
    });

    // تحديث القيم الغذائية عند تغيير الكمية أو اسم المكون
    $(document).on('input', '.ingredient_name', function () {
        const ingredientDiv = $(this).closest('.ingredient');
        const ingredientName = ingredientDiv.find('.ingredient_name').val();

        if (ingredientName) {
            $.ajax({
                url: '/get_nutrition',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    ingredient_name: ingredientName,
                    quantity: 100  // الكمية الافتراضية
                }),
                success: function (response) {
                    // تعبئة الكمية الافتراضية
                    ingredientDiv.find('.quantity').val(response.default_quantity);

                    // تحديث القيم الغذائية
                    ingredientDiv.find('.calories').text(response.calories.toFixed(2));
                    ingredientDiv.find('.protein').text(response.protein.toFixed(2));
                    ingredientDiv.find('.fat').text(response.fat.toFixed(2));
                    ingredientDiv.find('.carbs').text(response.carbohydrates.toFixed(2));
                }
            });
        }
    });

    // تحديث القيم الغذائية عند تغيير الكمية يدويًا
    $(document).on('input', '.quantity', function () {
        const ingredientDiv = $(this).closest('.ingredient');
        const ingredientName = ingredientDiv.find('.ingredient_name').val();
        const quantity = ingredientDiv.find('.quantity').val();

        if (ingredientName && quantity) {
            $.ajax({
                url: '/get_nutrition',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    ingredient_name: ingredientName,
                    quantity: quantity
                }),
                success: function (response) {
                    ingredientDiv.find('.calories').text(response.calories.toFixed(2));
                    ingredientDiv.find('.protein').text(response.protein.toFixed(2));
                    ingredientDiv.find('.fat').text(response.fat.toFixed(2));
                    ingredientDiv.find('.carbs').text(response.carbohydrates.toFixed(2));
                }
            });
        }
    });

    // حفظ الوجبة
    $('#mealForm').submit(function (e) {
        e.preventDefault();
        const mealNameAr = $('#meal_name_ar').val();
        const mealNameEn = $('#meal_name_en').val();
        const mealCategory = $('#meal_category').val();
        const mealImage = $('#meal_image')[0].files[0];
        const ingredients = [];

        $('.ingredient').each(function () {
            const ingredientName = $(this).find('.ingredient_name').val();
            const quantity = $(this).find('.quantity').val();
            const calories = $(this).find('.calories').text();
            const protein = $(this).find('.protein').text();
            const fat = $(this).find('.fat').text();
            const carbs = $(this).find('.carbs').text();

            ingredients.push({
                name: ingredientName,
                quantity: parseFloat(quantity),
                calories: parseFloat(calories),
                protein: parseFloat(protein),
                fat: parseFloat(fat),
                carbohydrates: parseFloat(carbs)
            });
        });

        const formData = new FormData();
        formData.append('meal_name_ar', mealNameAr);
        formData.append('meal_name_en', mealNameEn);
        formData.append('meal_category', mealCategory);
        formData.append('meal_image', mealImage);
        formData.append('ingredients', JSON.stringify(ingredients));

        $.ajax({
            url: '/save_meal',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                alert(response.message);
                if (response.qr_code_url) {
                    $('#qrCodeImage').attr('src', response.qr_code_url);
                    $('#qrCodeSection').show();
                }
            }
        });
    });
});