#include <iostream>
#include <string>
#include <FL/Fl.H>
#include <FL/Fl_Double_Window.H>
#include <FL/Fl_Native_File_Chooser.H>
#include <FL/Fl_Text_Display.H>
#include <FL/Fl_Button.H>
#include <FL/Fl_Box.H>
#include <cstdlib>

bool support_DJVU = true;
bool support_PDF = true;
bool support_DOC = true;
bool support_EPUB = true;


Fl_Double_Window* wstart = nullptr;
Fl_Text_Display* l = nullptr;
Fl_Button* bc = nullptr;
Fl_Button* ba = nullptr;

Fl_Double_Window* wmain = nullptr;
Fl_Double_Window* wfile_browser = nullptr;
Fl_Button* b_input_files = nullptr;
Fl_Box* b_input_files_count = nullptr;
Fl_Button* b_output_dir = nullptr;
Fl_Box* b_output_dir_label = nullptr;

std::string input_files_count_str;
std::string output_dir_str;

int call(std::string c) {
    std::string buffer;
    buffer.append(c);
    buffer.append(" > /dev/null 2>&1");
    return system(buffer.c_str());
};

int check_dependencies() {
    int dep_count = 0;

    // Check: ddjvu --help (expected 256)
    {
        int res = call("ddjvu --help");
        if (res == 32512) {
            l->insert("Command not found: ddjvu. Make sure to install djvulibre or djvulibre-bin package\n");
        }
        else if (res == 256) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 256 from ddjvu --help\n";
            l->insert(msg.c_str());
        }
    }

    // Check: djvused --help (expected 2560)
    {
        int res = call("djvused --help");
        if (res == 32512) {
            l->insert("Command not found: djvused. Make sure to install djvulibre or djvulibre-bin package\n");
        }
        else if (res == 2560) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 2560 from djvused --help\n";
            l->insert(msg.c_str());
        }
    }

    // Check: soffice --version (expected 0)
    {
        int res = call("soffice --version");
        if (res == 32512) {
            l->insert("Command not found: soffice. Make sure to install libreoffice package\n");
        }
        else if (res == 0) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 0 from soffice --version\n";
            l->insert(msg.c_str());
        }
    }

    // Check: pdfimages -v (expected 0)
    {
        int res = call("pdfimages -v");
        if (res == 32512) {
            l->insert("Command not found: pdfimages. Make sure to install poppler-utils\n");
        }
        else if (res == 0) dep_count++;
        else {
            std::string msg = std::string("Unexpected exitcode (") + std::to_string(res) + "), expected 0 from pdfimages -v\n";
            l->insert(msg.c_str());
        }
    }

    return dep_count;
}

void check_deps(void* user_data) {
    const int total_deps = 4;

    l->insert("Checking dependencies...\n");
    int dep_count = check_dependencies();
    {
        std::string msg = std::string("Dependencies: ") + std::to_string(dep_count) + "/" + std::to_string(total_deps) + "\n";
        l->insert(msg.c_str());
    }
    
    if (dep_count == 0) {
        l->insert("No dependencies found. Please install dependencies and restart in order to continue.");
    } else if (dep_count < total_deps) {
        l->insert("Some dependencies were not found. Would you like to still continue?");
        bc->show();
    } else {
        l->insert("All dependencies found!");
        wstart->hide();
        wmain->show();
        // bc->show();
    }
}

static void quit_cb(Fl_Widget* o) {
    exit(0);
}

static void bc_cb(Fl_Widget* o) {
    wstart->hide();
    wmain->show();
}

static void input_docs_cb(Fl_Widget* o) {
    Fl_Native_File_Chooser infc;
    infc.title("Choose documents to extract images from");
    infc.type(Fl_Native_File_Chooser::BROWSE_MULTI_FILE);
    infc.directory(".");
    if (infc.show() == 0) { // 0 means file chosen (not error or cancel)
        input_files_count_str = std::to_string(infc.count()) + std::string(" file(s)");
        b_input_files_count->label(input_files_count_str.c_str());
        b_input_files_count->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);
    } else {
        // std::cout << "Cancelled or Error." << std::endl;
    }
}

static void output_dir_cb(Fl_Widget* o) {
    Fl_Native_File_Chooser onfc;
    onfc.title("Choose directory to save images to");
    onfc.type(Fl_Native_File_Chooser::BROWSE_DIRECTORY);
    onfc.directory(".");
    if (onfc.show() == 0) { // 0 means file chosen (not error or cancel)
        output_dir_str = std::string(onfc.filename());
        b_output_dir_label->label(output_dir_str.c_str());
        b_output_dir_label->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);
    } else {
        // std::cout << "Cancelled or Error." << std::endl;
    }
}


int main(int argc, char **argv) {
    
    wstart = new Fl_Double_Window(600, 256);
    
    {
        l = new Fl_Text_Display(5, 5, 590, 196);
        Fl_Text_Buffer* buff = new Fl_Text_Buffer();
        l->buffer(buff);
        
        Fl::add_timeout(0, check_deps);
        
        bc = new Fl_Button(80, 196+10, 74, 32, "Continue");
        bc->hide();
        bc->callback(bc_cb);
        ba = new Fl_Button(5, 196+10, 64, 32, "Abort");
        ba->callback(quit_cb);
    }
    wstart->end();

    wmain = new Fl_Double_Window(512, 256);
    {
        new Fl_Box(50, 20, 200, 10, "Choose documents to extract images from.");
        b_input_files = new Fl_Button(10, 40, 128, 32, "Choose");
        b_input_files->callback(input_docs_cb);
        b_input_files_count = new Fl_Box(148, 48, 96, 24);
        new Fl_Box(30, 88, 120, 10, "Choose output directory.");
        b_output_dir = new Fl_Button(10, 108, 128, 32, "Choose");
        b_output_dir->callback(output_dir_cb);
        b_output_dir_label = new Fl_Box(148, 112, 356, 24);

        Fl_Button* quitb = new Fl_Button(512-74, 10, 64, 32, "Exit");
        quitb->callback(quit_cb);
    }
    wmain->end();

    wstart->show(argc, argv);

    return Fl::run();
};
