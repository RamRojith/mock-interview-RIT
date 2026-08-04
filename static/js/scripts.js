document.addEventListener('DOMContentLoaded', function () {
  const addRoleButton = document.getElementById('addRoleButton');
  const rolesContainer = document.getElementById('rolesContainer');
  let roleCount = 1;

  // Function to add new role input field
  addRoleButton.addEventListener('click', function () {
    roleCount++;
    console.log(roleCount + " dfsfs");

    const newRoleDiv = document.createElement('div');
    newRoleDiv.classList.add('row', 'mb-3');

    newRoleDiv.innerHTML = `
      <div class="col">
        <label for="roleName${roleCount}" class="form-label fw-semibold">Role Name</label>
        <input type="text" class="form-control" id="roleName${roleCount}" name="role[]" placeholder="Enter role name">
      </div>
      <div class="col-auto d-flex align-items-end">
        <button type="button" class="btn btn-outline-danger remove-role-btn">Remove</button>
      </div>
    `;

    rolesContainer.appendChild(newRoleDiv);

    // Attach the remove functionality to the "Remove" button
    newRoleDiv.querySelector('.remove-role-btn').addEventListener('click', function () {
      rolesContainer.removeChild(newRoleDiv);
    });
  });
});

  // JavaScript to dynamically add department fields
  document.addEventListener('DOMContentLoaded', function () {
    const addDepartmentButton = document.getElementById('addDepartmentBtn');
    const departmentList = document.getElementById('departmentList');
    let departmentCount = 1;
  
    // Function to add new department input fields
    addDepartmentButton.addEventListener('click', function () {
      departmentCount++;
      const newDepartmentDiv = document.createElement('div');
      newDepartmentDiv.classList.add('row', 'mb-3');
      newDepartmentDiv.innerHTML = `
        <div class="department-entry mb-3">
          <label for="departmentName${departmentCount}" class="form-label fw-semibold">Department Name</label>
          <input type="text" class="form-control" id="departmentName${departmentCount}" name="departmentName[]" placeholder="Enter department name" required>
        </div>
        <div class="department-entry mb-3">
          <label for="departmentCode${departmentCount}" class="form-label fw-semibold">Department Code</label>
          <input type="text" class="form-control" id="departmentCode${departmentCount}" name="departmentCode[]" placeholder="Enter department code" required>
        </div>
        <div class="col-auto d-flex align-items-end">
          <button type="button" class="btn btn-outline-danger remove-department-btn">Remove</button>
        </div>
      `;
  
      departmentList.appendChild(newDepartmentDiv);
  
      // Add event listener to "Remove" button
      newDepartmentDiv.querySelector('.remove-department-btn').addEventListener('click', function () {
        departmentList.removeChild(newDepartmentDiv);
      });
    });
  });
  

// Update view based on checkboxes
function updateView(id, checkbox) {
  const functionList = document.getElementById('functionList');
  const functionName = checkbox.getAttribute('data-function');

  if (checkbox.checked) {
    const listItem = document.createElement('li');
    listItem.textContent = `${functionName} (ID: ${id})`;
    listItem.classList.add('list-group-item');
    listItem.setAttribute('data-id', id);
    functionList.appendChild(listItem);
  } else {
    const items = functionList.querySelectorAll(`[data-id="${id}"]`);
    items.forEach(item => functionList.removeChild(item));
  }
}


// Function to handle individual checkbox state changes
function updateView(per, checkbox) {
  const isChecked = checkbox.checked;
  const functionList = document.getElementById('functionList');
  const listItemId = `function-${per}-${checkbox.getAttribute('data-id')}`;

  // Add or remove the item from the selected list
  if (isChecked) {
      if (!document.getElementById(listItemId)) {
          const li = document.createElement('li');
          li.id = listItemId;
          li.className = 'list-group-item';
          li.textContent = `${per} - ${checkbox.getAttribute('data-id')}`;
          functionList.appendChild(li);
      }
  } else {
      const li = document.getElementById(listItemId);
      if (li) {
          li.remove();
      }
  }
}

// Function to toggle all checkboxes
function toggleSelectAll() {
  const selectAllCheckbox = document.getElementById('selectAll');
  const checkboxes = document.querySelectorAll('.functionCheckbox');
  checkboxes.forEach(checkbox => {
      checkbox.checked = selectAllCheckbox.checked;
      updateView(checkbox.getAttribute('data-function'), checkbox);
  });
}



function validateFileType() {
  var fileInput = document.getElementById('profile_img');
  var filePath = fileInput.value;
  var allowedExtensions = /(\.jpg|\.jpeg|\.png)$/i;
  if (!allowedExtensions.exec(filePath)) {
      alert('Please upload an image file (jpg, jpeg, png, gif).');
      fileInput.value = ''; // Clear the input
      return false;
  }
  return true;
}
function previewImage() {
  var file = document.getElementById('profile_img').files[0];  // Get the file selected by the user
  var reader = new FileReader();  // Create a FileReader object

  reader.onloadend = function() {
      // Set the src attribute of the image to the result from FileReader
      document.getElementById('profile-img').src = reader.result;
  };

  // If a file is selected, read it
  if (file) {
      reader.readAsDataURL(file);
  }
}
document.addEventListener('DOMContentLoaded', function () {
  const addCategoryButton = document.getElementById('addCategoryButton');
  const categoriesContainer = document.getElementById('categoriesContainer');
  let categoryCount = 1;

  // Function to add new category input field
  addCategoryButton.addEventListener('click', function () {
      categoryCount++;
      console.log(`Category Count: ${categoryCount}`);

      const newCategoryDiv = document.createElement('div');
      newCategoryDiv.classList.add('row', 'mb-3');

      newCategoryDiv.innerHTML = `
          <div class="col">
              <label for="categoryName${categoryCount}" class="form-label fw-semibold">Category Name</label>
              <input type="text" class="form-control" id="categoryName${categoryCount}" name="category[]" placeholder="Enter category name">
          </div>
          <div class="col-auto d-flex align-items-end">
              <button type="button" class="btn btn-outline-danger remove-category-btn">Remove</button>
          </div>
      `;

      categoriesContainer.appendChild(newCategoryDiv);

      // Attach remove functionality to the "Remove" button
      newCategoryDiv.querySelector('.remove-category-btn').addEventListener('click', function () {
          categoriesContainer.removeChild(newCategoryDiv);
      });
  });
});

document.addEventListener('DOMContentLoaded', function () {
  const addSubCategoryButton = document.getElementById('addSubCategoryButton');
  const subCategoriesContainer = document.getElementById('subCategoriesContainer');
  let subCategoryCount = 1;

  // Add new subcategory input fields
  addSubCategoryButton.addEventListener('click', function () {
      subCategoryCount++;

      const newSubCategoryDiv = document.createElement('div');
      newSubCategoryDiv.classList.add('row', 'mb-3');

      // Generate the category select options from the categories array
      let categoryOptions = '';
      categories.forEach(cat => {
          categoryOptions += `<option value="${cat.name}">${cat.name}</option>`;
      });

      newSubCategoryDiv.innerHTML = `
          <div class="category-entry mb-3">
              <label for="categorySelect${subCategoryCount}" class="form-label fw-semibold">Category</label>
              <select class="form-select" id="categorySelect${subCategoryCount}" name="category[]" required>
                  <option value="" hidden selected>Select Category</option>
                  ${categoryOptions}
              </select>
          </div>
          <div class="subcategory-entry mb-3">
              <label for="subCategoryName${subCategoryCount}" class="form-label fw-semibold">Subcategory Name</label>
              <input type="text" class="form-control" id="subCategoryName${subCategoryCount}" name="sub_category[]" placeholder="Enter subcategory name" required>
          </div>
      `;

      subCategoriesContainer.appendChild(newSubCategoryDiv);
  });
});


$(document).ready(function() {
  // Add new program of study input field dynamically
  $('#addProgramofstudyBtn').on('click', function() {
      let newInput = `
          <div class="row mb-3">
              <div class="col-md-12">
                  <label for="programofstudyName" class="control-label">Program of Study Name</label>
                  <input type="text" class="form-control" name="program_of_study_name[]" placeholder="Enter program name" required>
              </div>
          </div>
      `;
      $('#programofstudiesList').append(newInput);
  });

  // Handle form submission via AJAX
  $('#addProgramofstudiesForm').on('submit', function(event) {
      event.preventDefault();
      let formData = $(this).serialize();  // Serialize form data

      $.ajax({
          url: $(this).attr('action'),  // Form action URL
          type: 'POST',
          data: formData,
          success: function(response) {
              if(response.success) {
                  alert('Programs added successfully!');
                  $('#addProgramofstudiesModal').modal('hide');  // Close modal
                  $('#programofstudiesList').html(`
                      <div class="row mb-3">
                          <div class="col-md-12">
                              <label for="programofstudyName1" class="control-label">Program of Study Name</label>
                              <input type="text" class="form-control" id="programofstudyName1" name="program_of_study_name[]" placeholder="Enter program name" required>
                          </div>
                      </div>
                  `); // Reset to default input
              } else {
                  alert('Error: ' + response.message);
              }
          },
          error: function(xhr, status, error) {
              console.error(error);
              alert('An error occurred while saving data.');
          }
      });
  });
});
