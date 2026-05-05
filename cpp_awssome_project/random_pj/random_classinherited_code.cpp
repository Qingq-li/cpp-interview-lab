#include <iostream>
#include <memory>
#include <string>
#include <vector>

class WorkBase{
public:
  WorkBase(const int &value){ id_ = value;}
  // WorkBase(){ id_ = value;}
  // WorkBase(){ id_ = 0;}

  virtual ~WorkBase(){
    std::cout << "Using BASE Destructer >>>>>> " << std::endl;  
  }
  
  // virtual void process(){
  //   std::cout<<"BASE : Waiting for processing!   "<< std::endl;
  // };
  virtual void process() = 0;
  
  virtual void print() const{
    std::cout<< "ID: " << id_ << std::endl;
  }

  void base_print(){
    std::cout<< "BASE PRINT / "<< std::endl;
  }
  
protected:
  int id_;
};


/////////////////////// DOGWORKER ////////////////////
class DogWork : public WorkBase{
public:
  DogWork():WorkBase(0){
    std::cout<< "Init dog instance!" << std::endl;
  }
 ~DogWork() override{ 
    std::cout<< "Use dog destructer!" << std::endl;
  }
  void process() override{
    std::cout << "--- Processing  :" << name << std::endl;
    
  }

    void print() const override{
    std::cout<< "ID: " << id_ << " name: " << name << std::endl;
  }
  
  private:
    std::string name = "dog";
};

/////////////////////// DOGWORKER ////////////////////
class CatWork : public WorkBase{
public:
  CatWork():WorkBase(1){
    std::cout<< "Init cat instance!" << std::endl;
  }
  ~CatWork() override{
    std::cout<< "Use cat destructer!" << std::endl;
  }

  void process() override{
    std::cout << "--- Processing  :" << name << std::endl;
  }

    void print() const override{
    std::cout<< "ID: " << id_ << " name: " << name << std::endl;
  }
  
  private:
    std::string name = "cat";
};


int main(){
  // auto  base_ptr  = std::make_unique<WorkBase>();
  // std::unique_ptr<WorkBase> base_ptr;
  std::cout << "\n  ---- Init Work:  ---- " << std::endl;
  std::vector<std::unique_ptr<WorkBase>> work_vec_;
  work_vec_.reserve(2);
  std::unique_ptr<WorkBase> dog_ptr = std::make_unique<DogWork>();
  std::unique_ptr<WorkBase> cat_ptr = std::make_unique<CatWork>();
  work_vec_.push_back(std::move(dog_ptr));
  work_vec_.push_back(std::move(cat_ptr));

  // print work
  std::cout << "\n  ---- PRINT WORK STATUS:  ----" << std::endl;
  for(auto &work : work_vec_){
    work->base_print();
    work->print(); 
    work->process(); // dynamicaly binding
  }
  
  // dog_ptr->print();
  // cat_ptr->print();
  // Over the games
  std::cout << "\n ---- Over: ---- " << std::endl;
  return 0;
}















