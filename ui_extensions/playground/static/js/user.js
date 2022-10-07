const template = document.createElement('template');
template.innerHTML = `
    <div id="user-card">
        <img id="picture" height="128" width="128"><br>
        <div>Name: <span id="name"></span></div>
        <div>Country: <span id="country"></span></div>
        <div>Email: <span id="email"></span></div>
        <div>Phone: <span id="phone"></span></div>
        <div>Cell: <span id="cell"></span></div>
    </div>
`;

export class UserCardElement extends HTMLElement {

    connectedCallback() {
        const url = "/xui/playground/api/data";
        this.fetchUser(url);
    }

    async fetchUser(url) {
        const response = await fetch(url);
        this.renderComponent(await response.json());
    }

    renderComponent(data) {
        // Destructure our json payload received from API
        const {
            results: [{
                email: email,
                name: {
                    first, last
                },
                location: {
                    country: country
                },
                picture: {
                    large: picture_src
                },
                phone: phone,
                cell: cell
            }]
        } = data;

        // Update template with api data
        const templateContent = template.content.cloneNode(true);
        templateContent.querySelector('#name').innerText = first + " " + last;
        templateContent.querySelector('#picture').src = picture_src;
        templateContent.querySelector('#country').innerText = country;
        templateContent.querySelector('#email').innerText = email;
        templateContent.querySelector('#phone').innerText = phone;
        templateContent.querySelector('#cell').innerText = cell;

        this.attachShadow({mode: 'open'}).appendChild(templateContent);
    }

}

customElements.define('user-card', UserCardElement);
